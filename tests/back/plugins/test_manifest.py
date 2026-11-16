import pytest
from plugin_helpers import manifest

from DashAI.back.plugins.manifest.manifest import ManifestError, PluginManifest


def _manifest(**overrides):
    return {**manifest("column-rounder", dependencies=["numpy>=1.18.0"]), **overrides}


def test_a_valid_manifest_parses_and_ignores_unknown_fields():
    parsed = PluginManifest.from_dict(
        _manifest(plugin_dependencies=["plugin-b>=1,<2", "plugin-c"], future_field="x")
    )

    assert (parsed.id, parsed.version) == ("column-rounder", "1.0.0")
    assert parsed.dependencies == ["numpy>=1.18.0"]
    assert parsed.plugin_dependencies == ["plugin-b", "plugin-c"]
    assert parsed.plugin_specifiers == {"plugin-b": "<2,>=1"}
    assert not hasattr(parsed, "future_field")  # forward compatibility


@pytest.mark.parametrize("plugin_id", ["my-plugin", "tsv2", "a-b-c"])
def test_valid_ids_are_lowercase_with_single_dashes(plugin_id):
    assert PluginManifest.from_dict(_manifest(id=plugin_id)).id == plugin_id


@pytest.mark.parametrize("plugin_id", ["My-Plugin", "a_b", "dots.", "a--b", "nul"])
def test_other_ids_are_refused(plugin_id):
    with pytest.raises(ManifestError, match="id must be lowercase") as raised:
        PluginManifest.from_dict(_manifest(id=plugin_id))

    assert (raised.value.code, raised.value.params) == ("invalid_id", {"id": plugin_id})


def _author(url):
    return {"authors": [{"name": "X", "url": url}]}


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"dependencies": [">=1.0"]}, "dependencies"),  # PEP 508 needs a package name
        ({"plugin_dependencies": ["Plugin_B"]}, "plugin_dependencies"),  # not an id
        ({"plugin_dependencies": ["plugin-b", "plugin-b"]}, "plugin_dependencies"),
        ({"plugin_dependencies": ["plugin-b[x]>=1"]}, "plugin_dependencies"),
        (
            {"plugin_dependencies": ["plugin-b @ https://x.org/b.zip"]},
            "plugin_dependencies",
        ),
        ({"plugin_dependencies": ["column-rounder"]}, "plugin_dependencies"),  # itself
        (_author("javascript:alert(1)"), "authors.0.url"),
        (_author("github.com/janeroe"), "authors.0.url"),  # no scheme
        (_author("ftp://example.org"), "authors.0.url"),
        ({"project_urls": {"Homepage": "javascript:alert(1)"}}, "project_urls"),
    ],
)
def test_an_invalid_field_is_named(overrides, field):
    with pytest.raises(ManifestError) as raised:
        PluginManifest.from_dict(_manifest(**overrides))

    assert raised.value.code == "invalid_manifest"
    assert raised.value.params == {"fields": [field]}
