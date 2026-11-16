import pytest
from plugin_helpers import BROKEN, make_plugin

from DashAI.back.plugins.manifest.validator import PluginValidator


def test_validate_reads_the_components_without_running_the_code(tmp_path):
    code = BROKEN.format(cls="ColumnRounder")
    make_plugin(tmp_path, cls="ColumnRounder", code=code)

    manifest, result = PluginValidator.validate(tmp_path)

    assert result.is_valid
    assert manifest.components[0].name == "ColumnRounder"


def test_a_module_is_reported_once_however_many_classes_it_has(tmp_path):
    code = "import dashaitest_helper\nclass A: pass\nclass B: pass\n"
    make_plugin(
        tmp_path,
        code=code,
        components=[
            {"class": f"mod:{name}", "type": "Converter"} for name in ("A", "B", "C")
        ],
    )
    (tmp_path / "dashaitest_helper.py").write_text("")

    _, result = PluginValidator.validate(tmp_path)

    assert [(e.code, e.params) for e in result.errors] == [
        ("class_not_defined", {"class": "C", "module": "mod"}),
        (
            "absolute_own_import",
            {
                "module": "mod",
                "name": "dashaitest_helper",
                "suggestion": "from . import dashaitest_helper",
            },
        ),
    ]


def _write(root, files):
    for name, content in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(content, encoding="utf-8")


def _own_imports(result):
    return [
        (e.params["module"], e.params["suggestion"])
        for e in result.errors
        if e.code == "absolute_own_import"
    ]


def test_an_absolute_import_of_its_own_code_is_found_in_every_module_it_imports(
    tmp_path,
):
    make_plugin(tmp_path, components=[{"class": "mypkg.model:C", "type": "Converter"}])
    _write(
        tmp_path / "src",
        {
            "mypkg/__init__.py": "",
            "mypkg/model.py": (
                "from .utils import K\nfrom .sub import deep\nclass C: pass\n"
            ),
            "mypkg/utils.py": "from mypkg.consts import K\n",
            "mypkg/consts.py": "K = 1\n",
            "mypkg/sub/__init__.py": "def f():\n    import mypkg.consts as c\n",
            "mypkg/sub/deep.py": "from mypkg import consts, utils as u\n",
        },
    )

    _, result = PluginValidator.validate(tmp_path)

    assert _own_imports(result) == [
        ("mypkg.utils", "from .consts import K"),
        ("mypkg.sub", "from .. import consts as c"),
        ("mypkg.sub.deep", "from .. import consts, utils as u"),
    ]


def test_an_absolute_import_of_its_own_code_is_refused_even_if_importable_outside(
    tmp_path, monkeypatch
):
    _write(tmp_path / "site", {"dashaitest_oldcopy/__init__.py": ""})
    monkeypatch.syspath_prepend(str(tmp_path / "site"))
    code = "from dashaitest_oldcopy import helper\nclass C: pass\n"
    make_plugin(tmp_path / "plugin", code=code)
    _write(tmp_path / "plugin", {"dashaitest_oldcopy/__init__.py": ""})

    _, result = PluginValidator.validate(tmp_path / "plugin")

    assert _own_imports(result) == [("mod", "from .dashaitest_oldcopy import helper")]


def test_data_folders_and_code_it_never_imports_are_not_checked(tmp_path):
    # json/ without __init__.py is data, so `import json` stays the stdlib one
    make_plugin(tmp_path, code="import json\nclass C: pass\n")
    _write(
        tmp_path, {"json/schema.json": "{}", "tests/test_mod.py": "from mod import C\n"}
    )

    _, result = PluginValidator.validate(tmp_path)

    assert result.is_valid


@pytest.mark.parametrize(
    ("fields", "codes"),
    [
        ({"min_app_version": "99.0.0"}, ["needs_newer_dashai"]),
        (
            {"components": [{"class": "mod:C", "type": "Optimizer"}]},
            ["type_not_allowed"],
        ),
        (  # every error at once
            {
                "min_app_version": "99.0.0",
                "components": [{"class": "x:Foo", "type": "Job"}],
            },
            ["module_not_found", "needs_newer_dashai", "type_not_allowed"],
        ),
    ],
)
def test_validate_reports_each_error(tmp_path, fields, codes):
    make_plugin(tmp_path, **fields)

    _, result = PluginValidator.validate(tmp_path)

    assert not result.is_valid
    assert sorted(error.code for error in result.errors) == codes
