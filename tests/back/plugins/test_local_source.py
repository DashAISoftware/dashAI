import pytest
from plugin_helpers import zip_bytes

from DashAI.back.plugins.sources.local_source import LocalSource, LocalSourceError


@pytest.mark.parametrize("wrap_in", [None, "my-plugin-1.0.0"])
def test_fetch_extracts_a_zip_at_root_or_in_its_single_folder(tmp_path, wrap_in):
    zip_path = tmp_path / "plugin.zip"
    zip_path.write_bytes(zip_bytes({"manifest.json": "{}"}, wrap_in=wrap_in))

    with LocalSource().fetch(str(zip_path)) as fetched:
        assert (fetched.path / "manifest.json").is_file()


def test_fetch_rejects_a_malicious_zip(tmp_path):
    zip_path = tmp_path / "evil.zip"
    zip_path.write_bytes(zip_bytes({"manifest.json": "{}", "../../evil.py": "pwn"}))

    with (
        pytest.raises(LocalSourceError, match="Unsafe path in zip"),
        LocalSource().fetch(str(zip_path)),
    ):
        pass

    assert not (tmp_path.parent / "evil.py").exists()
