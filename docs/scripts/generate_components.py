"""Generate Docusaurus MDX documentation for all DashAI registered components."""

import inspect
import json
import shutil
import sys
from pathlib import Path


def _escape_table_cell(text: str) -> str:
    """Escape characters that would break Markdown table columns or MDX parsing.

    MDX (used by Docusaurus) parses ``{`` / ``}`` as JSX expressions and
    ``<`` / ``>`` as JSX tags even inside Markdown table cells.  We replace
    them with HTML entities so the rendered output is correct while the MDX
    source remains valid.
    """
    s = str(text)
    s = s.replace("\n", " ")
    s = s.replace("|", "\\|")
    s = s.replace("{", "&#123;").replace("}", "&#125;")
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    return s


def _escape_mdx_text(text: str) -> str:
    """Escape ``<`` and ``>`` in plain MDX prose (outside of table cells).

    Curly braces in prose text are less common; we only escape angle brackets
    here because MDX/JSX will try to parse ``<word>`` as a JSX element.
    """
    s = str(text)
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    return s


SCRIPT_DIR = Path(__file__).parent
DOCS_ROOT = SCRIPT_DIR.parent  # docs/
COMPONENTS_OUT = DOCS_ROOT / "docs" / "components"


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------


def _extract_text(value, fallback="") -> str:
    """Extract a plain string from str, MultilingualString, or None."""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip()
    # Duck-type MultilingualString: has a callable .get method
    if callable(getattr(value, "get", None)):
        result = value.get("en")
        if result is None:
            return fallback
        return result.strip()
    return fallback


def _get_display_name(cls) -> str:
    """Return the component's display name, falling back to the class name."""
    raw = getattr(cls, "DISPLAY_NAME", None)
    name = _extract_text(raw)
    return name if name else cls.__name__


def _get_description(cls) -> str:
    """Return the component's description, falling back to the docstring."""
    raw = getattr(cls, "DESCRIPTION", None)
    desc = _extract_text(raw)
    if desc:
        return desc
    return (inspect.getdoc(cls) or "").strip()


def _get_short_description(cls) -> str:
    """Return the component's short description, falling back to description."""
    raw = getattr(cls, "SHORT_DESCRIPTION", None)
    short = _extract_text(raw)
    if short:
        return short
    return _get_description(cls)


def _get_compatible_components(cls) -> list:
    """Return the list of compatible component names."""
    return list(getattr(cls, "COMPATIBLE_COMPONENTS", None) or [])


def _format_default(prop: dict) -> str:
    """Extract a human-readable default value from a JSON Schema property dict.

    DashAI stores defaults under the 'placeholder' key (json_schema_extra).
    Falls back to 'default' for forward compatibility.
    """
    # DashAI primary location
    if "placeholder" in prop:
        val = prop["placeholder"]
        if isinstance(val, dict):
            # Optimizer placeholder dicts: show the fixed_value if present
            fixed = val.get("fixed_value")
            if fixed is not None:
                return str(fixed)
            return "—"
        return str(val)
    # Standard JSON Schema fallback
    if "default" in prop:
        return str(prop["default"])
    return "—"


def _get_schema_params(cls) -> list:
    """Parse the JSON Schema from get_schema() into a list of param dicts."""
    try:
        if not hasattr(cls, "get_schema"):
            return []
        schema = cls.get_schema()
        if schema is None:
            return []
        properties = schema.get("properties", {})
        params = []
        for name, prop in properties.items():
            raw_desc = prop.get("description", "")
            description = (
                _extract_text(raw_desc) if not isinstance(raw_desc, str) else raw_desc
            )
            params.append(
                {
                    "name": name,
                    "type": prop.get("type", ""),
                    "default": _format_default(prop),
                    "description": description,
                }
            )
        return params
    except Exception:
        return []


def _is_pipeline_node(cls) -> bool:
    """Return True if the class is from the DashAI pipeline module."""
    return getattr(cls, "__module__", "").startswith("DashAI.back.pipeline")


# ---------------------------------------------------------------------------
# Numpy docstring parser
# ---------------------------------------------------------------------------


def _parse_numpy_docstring(docstring: str) -> dict:
    """Parse a NumPy-style docstring into structured parts.

    Returns
    -------
    dict
        Keys: summary (str), parameters (list of {name, type, desc}),
        returns (list of {type, desc}).
    """
    result = {"summary": "", "parameters": [], "returns": []}
    if not docstring:
        return result

    lines = docstring.splitlines()

    # Extract summary: lines up to the first blank line OR first section header
    summary_lines = []
    i = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Stop at blank line
        if stripped == "" and summary_lines:
            break
        # Stop if next line is a section underline (----)
        if i + 1 < len(lines) and lines[i + 1].strip().startswith("---"):
            if stripped:
                summary_lines.append(stripped)
            break
        if stripped:
            summary_lines.append(stripped)
    result["summary"] = " ".join(summary_lines)

    # --- Scan for sections ---
    # A section header is a line followed by a line of dashes
    sections = {}  # section_name_lower -> list of lines
    current_section = None
    j = i + 1
    while j < len(lines):
        line = lines[j]
        # Check if the *next* line is all dashes (section header pattern)
        if (
            j + 1 < len(lines)
            and lines[j + 1].strip()
            and all(c == "-" for c in lines[j + 1].strip())
        ):
            current_section = line.strip().lower()
            sections[current_section] = []
            j += 2  # skip header and dashes line
            continue
        if current_section is not None:
            sections[current_section].append(line)
        j += 1

    # --- Parse Parameters section ---
    param_lines = sections.get("parameters", [])
    k = 0
    while k < len(param_lines):
        line = param_lines[k]
        # "name : type" or "name" pattern (non-indented)
        stripped = line.strip()
        if stripped and not line.startswith(" ") and not line.startswith("\t"):
            if " : " in stripped:
                parts = stripped.split(" : ", 1)
                pname = parts[0].strip()
                ptype = parts[1].strip()
            else:
                pname = stripped
                ptype = ""
            # Gather indented description lines
            desc_parts = []
            k += 1
            while k < len(param_lines):
                dline = param_lines[k]
                if dline.strip() == "":
                    k += 1
                    continue
                if dline.startswith((" ", "\t")):
                    desc_parts.append(dline.strip())
                    k += 1
                else:
                    break
            result["parameters"].append(
                {
                    "name": pname,
                    "type": ptype,
                    "desc": " ".join(desc_parts),
                }
            )
        else:
            k += 1

    # --- Parse Returns section ---
    return_lines = sections.get("returns", [])
    k = 0
    while k < len(return_lines):
        line = return_lines[k]
        stripped = line.strip()
        if stripped and not line.startswith(" ") and not line.startswith("\t"):
            rtype = stripped
            # Gather indented description lines
            desc_parts = []
            k += 1
            while k < len(return_lines):
                dline = return_lines[k]
                if dline.strip() == "":
                    k += 1
                    continue
                if dline.startswith((" ", "\t")):
                    desc_parts.append(dline.strip())
                    k += 1
                else:
                    break
            result["returns"].append(
                {
                    "type": rtype,
                    "desc": " ".join(desc_parts),
                }
            )
        else:
            k += 1

    return result


# ---------------------------------------------------------------------------
# Method extraction
# ---------------------------------------------------------------------------


def _get_methods(cls) -> list:
    """Extract public methods from the class and its MRO.

    Returns own methods (defined on cls) sorted alphabetically, followed by
    inherited methods sorted alphabetically.
    """
    collected = {}  # name -> method dict (child wins over parent)

    root_module = getattr(cls, "__module__", "")

    # Walk MRO in reverse so child definitions overwrite parent ones
    for klass in reversed(cls.__mro__):
        if klass is object:
            continue
        # Include methods defined on DashAI classes and on classes from the
        # same module as the target class (useful for local/testing classes).
        klass_module = getattr(klass, "__module__", "")
        if not (klass_module.startswith("DashAI") or klass_module == root_module):
            continue
        for name, obj in vars(klass).items():
            if name.startswith("_"):
                continue
            # Resolve classmethods and staticmethods
            if isinstance(obj, (classmethod, staticmethod)):
                func = obj.__func__
            elif inspect.isfunction(obj):
                func = obj
            else:
                continue

            if not callable(func):
                continue

            # Get signature
            try:
                sig = str(inspect.signature(func))
            except (ValueError, TypeError):
                sig = "(...)"

            # Get docstring
            docstring = inspect.getdoc(func) or ""
            parsed = _parse_numpy_docstring(docstring)

            collected[name] = {
                "name": name,
                "signature": sig,
                "defined_on": klass.__name__,
                "summary": parsed["summary"],
                "parameters": parsed["parameters"],
                "returns": parsed["returns"],
            }

    # Split into own vs inherited
    own = []
    inherited = []
    for _name, info in collected.items():
        if info["defined_on"] == cls.__name__:
            own.append(info)
        else:
            inherited.append(info)

    own.sort(key=lambda m: m["name"])
    inherited.sort(key=lambda m: m["name"])

    return own + inherited


# ---------------------------------------------------------------------------
# MDX rendering
# ---------------------------------------------------------------------------


def _render_method_section(method) -> str:
    """Render one method as an MDX section."""
    lines = []
    defined_on = method["defined_on"]
    lines.append(
        f" `{method['name']}{method['signature']}` "
        f"<small>defined on `{defined_on}`</small>"
    )
    lines.append("")
    if method["summary"]:
        lines.append(_escape_mdx_text(method["summary"]))
        lines.append("")

    if method["parameters"]:
        lines.append("**Parameters**")
        lines.append("")
        lines.append("| Name | Type | Description |")
        lines.append("|------|------|-------------|")
        for p in method["parameters"]:
            name = _escape_table_cell(p["name"])
            ptype = _escape_table_cell(p["type"])
            desc = _escape_table_cell(p["desc"])
            lines.append(f"| {name} | {ptype} | {desc} |")
        lines.append("")

    if method["returns"]:
        lines.append("**Returns**")
        lines.append("")
        lines.append("| Type | Description |")
        lines.append("|------|-------------|")
        for r in method["returns"]:
            lines.append(
                f"| {_escape_table_cell(r['type'])} | {_escape_table_cell(r['desc'])} |"
            )
        lines.append("")

    return "\n".join(lines)


def _render_component_mdx(info) -> str:
    """Render a component info dict as an MDX string."""
    class_name = info["class_name"]
    display_name = info["display_name"]
    component_type = info["type"]
    description = info["description"]
    params = info["params"]
    methods = info["methods"]
    compatible = info["compatible"]

    lines = []
    lines.append("---")
    title = info["class_name"].replace('"', '\\"')
    sidebar = (info["display_name"] or info["class_name"]).replace('"', '\\"')
    lines.append(f'title: "{title}"')
    lines.append(f'sidebar_label: "{sidebar}"')
    lines.append("---")
    lines.append("")
    lines.append(f"# {class_name}")
    lines.append("")
    lines.append(f"**Type:** {component_type}  ")
    lines.append(f"**Display name:** {display_name}")
    lines.append("")

    lines.append("## Description")
    lines.append("")
    lines.append(description if description else "_No description available._")
    lines.append("")

    if params:
        lines.append("## Parameters")
        lines.append("")
        lines.append("| Name | Type | Default | Description |")
        lines.append("|------|------|---------|-------------|")
        for p in params:
            name = _escape_table_cell(p["name"])
            ptype = _escape_table_cell(p["type"])
            default = _escape_table_cell(p["default"])
            description = _escape_table_cell(p["description"])
            lines.append(f"| {name} | {ptype} | {default} | {description} |")
        lines.append("")

    if methods:
        lines.append("## Methods")
        lines.append("")
        for method in methods:
            lines.append(_render_method_section(method))

    if compatible:
        lines.append("## Compatible with")
        lines.append("")
        for comp in compatible:
            lines.append(f"- {comp}")
        lines.append("")

    return "\n".join(lines)


def _render_index_mdx(type_label: str, components: list) -> str:
    """Render an index MDX page for a component type.

    Parameters
    ----------
    type_label : str
        Singular type name, e.g. "Model" or "Converter".
    components : list
        List of dicts with keys: class_name, display_name, short_description.
    """
    plural = type_label + "s"
    sorted_components = sorted(components, key=lambda c: c["class_name"])

    lines = []
    lines.append("---")
    lines.append(f"title: {plural}")
    lines.append(f"sidebar_label: All {plural}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {plural}")
    lines.append("")
    lines.append(f"All registered `{type_label}` components in DashAI.")
    lines.append("")
    lines.append("| Name | Description |")
    lines.append("|------|-------------|")
    for comp in sorted_components:
        short = _escape_table_cell(comp["short_description"])
        lines.append(f"| [{comp['class_name']}](./{comp['class_name']}) | {short} |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Category configuration
# ---------------------------------------------------------------------------

CATEGORY_CONFIG: dict[str, dict] = {
    "task": {"label": "Tasks", "position": 1},
    "model": {"label": "Models", "position": 2},
    "generativemodel": {"label": "Generative Models", "position": 3},
    "dataloader": {"label": "Data Loaders", "position": 4},
    "metric": {"label": "Metrics", "position": 5},
    "optimizer": {"label": "Optimizers", "position": 6},
    "explorer": {"label": "Explorers", "position": 7},
    "globalexplainer": {"label": "Global Explainers", "position": 8},
    "localexplainer": {"label": "Local Explainers", "position": 9},
    "converter": {"label": "Converters", "position": 10},
    "job": {"label": "Jobs", "position": 11},
    "generativetask": {"label": "Generative Tasks", "position": 12},
}


def _type_to_dir(component_type: str) -> str:
    """Convert a component TYPE to a directory name, e.g. 'Model' -> 'models'."""
    return component_type.lower() + "s"


def _render_category_json(type_key: str) -> str:
    """Render the _category_.json content for a component type directory."""
    cfg = CATEGORY_CONFIG.get(
        type_key, {"label": type_key.capitalize() + "s", "position": 99}
    )
    data = {
        "label": cfg["label"],
        "position": cfg["position"],
        "collapsible": True,
        "collapsed": False,
    }
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------


def generate_all(output_dir=None):
    """Generate all component MDX files.

    Parameters
    ----------
    output_dir : Path or str, optional
        Override output directory. Defaults to COMPONENTS_OUT.
    """
    # Add repo root to sys.path if not already there
    repo_root = str(SCRIPT_DIR.parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from DashAI.back.initial_components import get_initial_components  # noqa: E402

    out_dir = Path(output_dir) if output_dir else COMPONENTS_OUT

    # Deduplicate components preserving order
    all_components = list(dict.fromkeys(get_initial_components()))

    # Filter out pipeline nodes
    components = [c for c in all_components if not _is_pipeline_node(c)]

    # Clear and recreate output directory
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group by TYPE
    type_groups: dict = {}
    for cls in components:
        t = getattr(cls, "TYPE", "Unknown")
        type_groups.setdefault(t, []).append(cls)

    total = 0
    for component_type, cls_list in sorted(type_groups.items()):
        type_key = component_type.lower()
        type_dir = out_dir / _type_to_dir(component_type)
        type_dir.mkdir(parents=True, exist_ok=True)

        # Write _category_.json
        category_json = _render_category_json(type_key)
        (type_dir / "_category_.json").write_text(category_json, encoding="utf-8")

        index_entries = []

        for cls in cls_list:
            display_name = _get_display_name(cls)
            description = _get_description(cls)
            short_description = _get_short_description(cls)
            params = _get_schema_params(cls)
            methods = _get_methods(cls)
            compatible = _get_compatible_components(cls)

            info = {
                "class_name": cls.__name__,
                "type": component_type,
                "display_name": display_name,
                "description": description,
                "params": params,
                "methods": methods,
                "compatible": compatible,
            }

            mdx = _render_component_mdx(info)
            (type_dir / f"{cls.__name__}.mdx").write_text(mdx, encoding="utf-8")
            total += 1

            index_entries.append(
                {
                    "class_name": cls.__name__,
                    "display_name": display_name,
                    "short_description": short_description,
                }
            )

        # Write index.mdx
        index_mdx = _render_index_mdx(component_type, index_entries)
        (type_dir / "index.mdx").write_text(index_mdx, encoding="utf-8")

        rel_type_dir = type_dir.relative_to(out_dir.parent.parent)
        print(f"  {component_type}: {len(cls_list)} components -> {rel_type_dir}")

    print(f"\nTotal: {total} component pages written to {out_dir}")


if __name__ == "__main__":
    generate_all()
