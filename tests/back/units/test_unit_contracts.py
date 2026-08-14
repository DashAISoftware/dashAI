"""A contract audit over every registered unit, enforced as a test.

The individual unit tests check behaviour; this one checks that the *declared*
contract matches the code. Undeclared context reads are the recurring mistake in
this design: they never break the job that happens to wire the context by hand,
so they survive every end-to-end test and only surface when something reuses the
unit — which is the whole point of having units.
"""

import ast
import pathlib

import pytest

UNITS_DIR = pathlib.Path(__file__).resolve().parents[3] / "DashAI" / "back" / "units"

#: Keys a unit reads that its own execution produces, so they need no declaration.
SELF_PRODUCED = {"dataset"}


def _unit_modules():
    for path in sorted(UNITS_DIR.glob("*.py")):
        if path.name in {"__init__.py", "base_unit.py", "context.py"}:
            continue
        yield path


def _string_literals(node):
    return {
        element.value
        for element in ast.walk(node)
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    }


def _unit_class(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and any(
            isinstance(base, ast.Name) and base.id == "BaseUnit" for base in node.bases
        ):
            return node
    return None


def _declared(cls, name):
    for node in cls.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return _string_literals(node.value)
    return set()


def _context_calls(cls, methods):
    """Every ``ctx.<method>("key")`` literal inside the class."""
    keys = set()
    for node in ast.walk(cls):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in methods
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "ctx"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
    return keys


def _parsed_units():
    units = []
    for path in _unit_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        cls = _unit_class(tree)
        if cls is not None:
            units.append((path.name, cls))
    return units


UNITS = _parsed_units()


def test_the_audit_actually_found_the_units():
    """Guards the audit itself: a broken parser would make it vacuously pass."""
    assert {name for name, _ in UNITS} >= {
        "load_dataset_unit.py",
        "apply_converter_unit.py",
        "save_dataset_unit.py",
    }


@pytest.mark.parametrize(("name", "cls"), UNITS, ids=[name for name, _ in UNITS])
def test_every_context_key_a_unit_reads_is_declared_in_requires(name, cls):
    read = _context_calls(cls, {"require", "get", "has"})
    declared = _declared(cls, "REQUIRES") | _declared(cls, "PROVIDES") | SELF_PRODUCED

    undeclared = read - declared
    assert not undeclared, (
        f"{name} reads {sorted(undeclared)} from the context without declaring "
        "them in REQUIRES. A caller inspecting the contract cannot know they "
        "are needed, and a missing value reads as 'not applicable' instead of "
        "'wiring mistake'."
    )


@pytest.mark.parametrize(("name", "cls"), UNITS, ids=[name for name, _ in UNITS])
def test_a_unit_does_not_require_a_key_it_never_reads(name, cls):
    """The mirror of the test above, and just as load-bearing.

    ``__call__`` demands every key in ``REQUIRES`` unconditionally, so a key
    listed but never read is not harmless documentation: it rejects any upstream
    that does not happen to publish it. ``PrepareExplanationDataUnit`` used to
    require ``dataset_id`` — left over from an error message that moved to the
    job — which would have made it impossible to compose after
    ``BuildManualInputUnit``, whose ``PROVIDES`` is just ``("dataset",)``.

    It passed every end-to-end test because the one job wiring it happened to
    run a loader that publishes the id first. That is exactly the class of
    mistake this file exists to catch.
    """
    required = _declared(cls, "REQUIRES")
    read = _context_calls(cls, {"require", "get", "has"})

    unread = required - read
    assert not unread, (
        f"{name} declares {sorted(unread)} in REQUIRES but never reads them. "
        "Every declared key is demanded before the unit runs, so an unused one "
        "only narrows what the unit can be composed after."
    )


@pytest.mark.parametrize(("name", "cls"), UNITS, ids=[name for name, _ in UNITS])
def test_every_key_a_unit_promises_is_actually_written(name, cls):
    written = _context_calls(cls, {"put", "put_ref"})
    promised = _declared(cls, "PROVIDES")

    unwritten = promised - written
    assert not unwritten, (
        f"{name} promises {sorted(unwritten)} in PROVIDES but never writes it."
    )


@pytest.mark.parametrize(("name", "cls"), UNITS, ids=[name for name, _ in UNITS])
def test_a_unit_does_not_use_the_context_as_its_own_scratchpad(name, cls):
    """A key written and read by the same unit, and promised to nobody.

    That is instance state wearing a context key's clothes: two units of the
    same class in one context would overwrite each other. It belongs on
    ``self``, memoized, the way the registry lookups are.
    """
    written = _context_calls(cls, {"put", "put_ref"})
    read = _context_calls(cls, {"require", "get", "has"})
    promised = _declared(cls, "PROVIDES")

    scratch = (written & read) - promised - SELF_PRODUCED
    assert not scratch, (
        f"{name} writes and reads {sorted(scratch)} without promising it. "
        "Keep per-instance state on the unit, not in the shared context."
    )
