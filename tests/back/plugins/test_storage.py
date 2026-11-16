import json
import os

import pytest
from plugin_helpers import make_plugin

from DashAI.back.plugins.disk.storage import Provenance
from DashAI.back.plugins.disk.trash import Trash


def _save(storage, plugin_id, source):
    trash = Trash(storage.root)
    stored = storage.save(plugin_id, source, Provenance("local", "a.zip"), trash)
    trash.commit()
    return stored


@pytest.mark.parametrize("bad_id", ["../evil", "a/b", "a\\b", "..", ""])
def test_plugin_dir_rejects_unsafe_ids(storage, bad_id):
    with pytest.raises(ValueError, match="Invalid plugin id"):
        storage.plugin_dir(bad_id)


def test_save_copies_a_link_to_a_parent_folder_as_a_link(tmp_path, storage):
    # The data filter allows "loop -> .", which copytree would follow forever
    source = make_plugin(tmp_path / "source", "calendar")
    try:
        os.symlink(".", source / "loop", target_is_directory=True)
    except OSError:
        pytest.skip("this system can't create symlinks")

    stored = _save(storage, "calendar", source)

    assert (stored.path / "loop").is_symlink()


@pytest.mark.parametrize(
    "marker",
    [
        {"source": "local", "location": "a.zip", "extra": 1},  # a newer dashAI's
        {"source": 1, "location": ""},
    ],
)
def test_a_source_marker_this_dashai_did_not_write_is_refused(
    tmp_path, storage, marker
):
    _save(storage, "calendar", make_plugin(tmp_path / "source", "calendar"))
    (storage.plugin_dir("calendar") / ".source").write_text(json.dumps(marker))

    with pytest.raises(ValueError, match="validation error"):
        storage.read_source("calendar")
