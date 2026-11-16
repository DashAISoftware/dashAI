import json

import pytest

from DashAI.back.plugins.disk import previews
from DashAI.back.plugins.disk.previews import Preview, PreviewExpiredError
from DashAI.back.plugins.sources.base import Fetched


def _preview(tmp_path, name="plugin"):
    folder = tmp_path / "fetched" / name
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text('{"id": "demo"}', encoding="utf-8")
    fetched = Fetched(folder, "v1", "github_attested", True, "ab" * 32, "c0ffee")
    return Preview("git", "https://github.com/o/r", fetched)


def _saved(root):
    folder = root / previews.PREVIEWS_DIR
    return sorted(entry.name for entry in folder.iterdir()) if folder.is_dir() else []


def _age(root, token, seconds):
    path = root / previews.PREVIEWS_DIR / token / "preview.json"
    data = json.loads(path.read_text("utf-8"))
    data["created_at"] -= seconds
    path.write_text(json.dumps(data), encoding="utf-8")


def test_only_one_install_gets_a_preview(tmp_path):
    root = tmp_path / "plugins"
    token = previews.save(root, _preview(tmp_path))

    with (
        previews.claim(root, token),
        pytest.raises(PreviewExpiredError),
        previews.claim(root, token),
    ):
        pass


@pytest.mark.parametrize(
    "token", ["missing-token-abcdefghi", "../plugins", "a/b", "..", ""]
)
def test_an_unknown_or_unsafe_token_is_expired(tmp_path, token):
    root = tmp_path / "plugins"
    (root / previews.PREVIEWS_DIR).mkdir(parents=True)

    with pytest.raises(PreviewExpiredError) as raised, previews.claim(root, token):
        pass

    assert raised.value.code == "preview_expired"
    previews.discard(root, token)  # never fails either
    assert root.is_dir()


def test_saving_keeps_the_newest_and_drops_old_ones(tmp_path):
    root = tmp_path / "plugins"
    tokens = [previews.save(root, _preview(tmp_path, f"p{i}")) for i in range(2)]
    _age(root, tokens[0], previews.MAX_AGE_SECONDS + 1)
    newer = [
        previews.save(root, _preview(tmp_path, f"q{i}"))
        for i in range(previews.MAX_PREVIEWS)
    ]

    assert _saved(root) == sorted(newer)


def test_sweep_leaves_a_preview_in_use_until_startup(tmp_path):
    root = tmp_path / "plugins"
    token = previews.save(root, _preview(tmp_path))

    with previews.claim(root, token):
        previews.sweep(root, keep=0)
        assert _saved(root) == [token + ".taken"]
        previews.sweep(root, taken=True)  # dashAI closed during an install
        assert _saved(root) == []
