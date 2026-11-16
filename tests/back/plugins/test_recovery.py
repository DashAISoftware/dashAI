"""Reopening after a crash mid-operation leaves it undone or fully done."""

import contextlib
import json
import os
import stat
import threading

import psutil
import pytest
from plugin_helpers import Env
from test_dependency_lifecycle import LIBX_V1

from DashAI.back.plugins.disk import trash as trash_module
from DashAI.back.plugins.disk.trash import Trash, recover
from DashAI.back.plugins.plugin_installer import PluginBusyError


def _half_done(env, plugin_id="p", **journal):
    """An uninstall of ``plugin_id`` that moved it to the trash and stopped."""
    trash = Trash(env.storage.root)
    trash.move(env.storage.plugin_dir(plugin_id))
    path = trash.folder / "journal.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), **journal}))
    return trash


@pytest.mark.parametrize("committed", [False, True])
def test_an_update_is_undone_unless_it_committed(tmp_path, committed):
    env = Env(tmp_path)
    env.install("p", "1.0.0", ["libx<2"], module=LIBX_V1, cls="C")
    transaction = env.deps.transaction()
    transaction.install(env.deps.resolve(["libx>=2"], []).distributions)
    if committed:
        transaction.commit()

    env.reopen()

    assert env.on_disk() == (["libx-2.0"] if committed else ["libx-1.0"])
    assert ("2.0" in (env.deps_dir / "libx.py").read_text()) is committed


@pytest.mark.parametrize("its_start_time", [True, False])
def test_an_operation_is_kept_only_while_the_dashai_doing_it_runs(
    tmp_path, its_start_time
):
    # Windows reuses pids, so a live pid with another start time is another program.
    env = Env(tmp_path)
    env.install("p")
    parent = psutil.Process(os.getppid())  # alive, and not this process
    started = {"started": parent.create_time()} if its_start_time else {}
    trash = _half_done(env, pid=parent.pid, **started)

    recover(env.storage.root)

    assert trash.folder.exists() is its_start_time
    assert env.storage.is_installed("p") is not its_start_time


def test_an_operation_waits_out_a_file_briefly_open_elsewhere(tmp_path):
    # Windows can't move a folder with an open file (worker, list, antivirus)
    env = Env(tmp_path)
    env.install("p")
    handle = (env.storage.plugin_dir("p") / "manifest.json").open("rb")
    threading.Timer(0.1, handle.close).start()

    env.installer.uninstall("p")

    assert not env.storage.is_installed("p")


def test_another_running_dashai_changing_plugins_makes_an_operation_wait(tmp_path):
    env = Env(tmp_path)
    process = psutil.Process().parent()  # another process, still running
    (env.storage.root / trash_module.OPERATION_MARKER).write_text(
        json.dumps({"pid": process.pid, "started": process.create_time()})
    )

    with pytest.raises(PluginBusyError, match="Another dashAI"):
        env.install("p")

    assert not env.storage.is_installed("p")


@pytest.mark.skipif(os.name != "nt", reason="a dot already hides them elsewhere")
def test_write_json_keeps_a_dotted_file_hidden_and_rewritable(tmp_path):
    # Windows refuses open("w") on a hidden file, and replacing shows it again
    def hidden(path):
        return bool(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)

    state, settings = tmp_path / ".store.json", tmp_path / "geo.json"
    for value in (1, 2):
        trash_module.write_json(state, {"v": value})
        trash_module.write_json(settings, {"v": value})

    assert json.loads(state.read_text("utf-8")) == {"v": 2}
    assert hidden(state)
    assert not hidden(settings)  # only dotted names


def test_a_nested_operation_keeps_the_marker_until_the_outermost_ends(tmp_path):
    with contextlib.ExitStack() as startup:
        startup.enter_context(trash_module.operation(tmp_path))

        def install():
            with trash_module.operation(tmp_path):
                pass

        backend = threading.Thread(target=install)
        backend.start()
        backend.join()

        assert trash_module.operation_running(tmp_path)
    assert not trash_module.operation_running(tmp_path)
