import pathlib
from unittest import mock

import pytest
from kink import di

from DashAI.back.dependencies.downloads import downloadable as dl

_SENTINEL = object()


@pytest.fixture
def components_root(tmp_path):
    # kink Container has no .get(), so monkeypatch.setitem is not usable.
    # Save and restore the "config" key manually.
    try:
        old = di["config"]
    except Exception:
        old = _SENTINEL
    di["config"] = {"COMPONENT_PATH": str(tmp_path)}
    yield pathlib.Path(tmp_path)
    if old is _SENTINEL:
        del di["config"]
    else:
        di["config"] = old


class _Dummy(dl.HFDownloadableMixin):
    HF_REPOS = [("owner/model-a", "model")]


def _populate(root: pathlib.Path, cls, repo_leaf: str):
    d = root / cls.__name__ / repo_leaf
    d.mkdir(parents=True)
    (d / "config.json").write_text("{}")


def test_component_dir_under_root(components_root):
    assert _Dummy.component_dir() == components_root / "_Dummy"


def test_is_downloaded_false_when_absent(components_root):
    assert _Dummy.is_downloaded() is False


def test_is_downloaded_true_when_present(components_root):
    _populate(components_root, _Dummy, "model-a")
    assert _Dummy.is_downloaded() is True


def test_is_downloaded_false_when_no_repos(components_root):
    class Empty(dl.HFDownloadableMixin):
        HF_REPOS = []

    assert Empty.is_downloaded() is False


def test_download_fetches_into_component_dir(components_root):
    calls = []
    with mock.patch.object(dl, "snapshot_download") as snap:
        _Dummy.download(lambda frac, msg: calls.append((frac, msg)))
    snap.assert_called_once()
    kwargs = snap.call_args.kwargs
    assert kwargs["repo_id"] == "owner/model-a"
    assert kwargs["local_dir"] == str(components_root / "_Dummy" / "model-a")
    assert calls  # progress was reported


def test_delete_removes_component_dir(components_root):
    _populate(components_root, _Dummy, "model-a")
    _Dummy.delete()
    assert not (components_root / "_Dummy").exists()
