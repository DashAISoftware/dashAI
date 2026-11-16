"""Outside data (folders, markers, manifests, archives) fails clearly, no crash."""

import codecs
import json
import zipfile
from pathlib import Path

import pytest
from plugin_helpers import Env

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.plugins.sources import base
from DashAI.back.plugins.sources.base import SourceError
from DashAI.back.plugins.sources.local_source import LocalSource


def test_markers_shipped_inside_a_plugin_are_ignored(tmp_path):
    env = Env(tmp_path)
    folder = Path(env.plugin("z", cls="C"))
    (folder / ".disabled").write_text("")
    (folder / ".source").write_text(json.dumps({"trust_level": "github_attested"}))

    env.installer.install(PluginSource.LOCAL, str(folder))

    assert env.storage.is_enabled("z")
    assert "C" in env.registry
    assert env.storage.read_source("z").trust_level == "local"


def test_a_zip_too_big_once_extracted_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "MAX_PLUGIN_BYTES", 1024)
    zip_path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("data.bin", b"\0" * 4096)

    with (
        pytest.raises(SourceError, match="too big"),
        LocalSource().fetch(str(zip_path)),
    ):
        pass


def test_a_manifest_with_a_bom_is_accepted(tmp_path):
    # Windows PowerShell 5.1 ("Set-Content -Encoding UTF8") and old Notepad add it.
    env = Env(tmp_path)
    manifest = Path(env.plugin("p")) / "manifest.json"
    manifest.write_bytes(codecs.BOM_UTF8 + manifest.read_bytes())

    result = env.installer.validate(PluginSource.LOCAL, str(manifest.parent))

    assert result.is_valid, result.errors
