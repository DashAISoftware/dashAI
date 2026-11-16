"""The plugin dependency lifecycle against the real pip, offline."""

import base64
import hashlib
import subprocess
import sys
import zipfile

import pytest
from plugin_helpers import BASE, Env

from DashAI.back.plugins.plugin_installer import PluginInstallError

pytest.importorskip("pip")

WHEELS = {
    ("dashaitestlib", "1.0"): {
        "files": {
            "dashaitestlib/__init__.py": "VERSION = '1.0'\n",
            "dashaitestlib_old.py": "",  # 2.0 no longer ships it
        }
    },
    ("dashaitestlib", "2.0"): {
        "files": {"dashaitestlib/__init__.py": "VERSION = '2.0'\n"}
    },
    ("dashaitestextra", "1.0"): {
        "files": {"dashaitestextra.py": ""},
        "extras": ["fast"],
        "requires": ['dashaitestspeed; extra == "fast"'],
    },
    ("dashaitestspeed", "1.0"): {"files": {"dashaitestspeed.py": ""}},
    ("dashaitestnew", "1.0"): {"files": {"dashaitestnew.py": ""}},
}


def _digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def _build_wheel(folder, name, version, spec):
    info = f"{name}-{version}.dist-info"
    contents = {path: text.encode() for path, text in spec["files"].items()}
    contents[f"{info}/METADATA"] = (
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
        + "".join(f"Provides-Extra: {e}\n" for e in spec.get("extras", []))
        + "".join(f"Requires-Dist: {r}\n" for r in spec.get("requires", []))
    ).encode()
    contents[f"{info}/WHEEL"] = (
        b"Wheel-Version: 1.0\nGenerator: dashai-tests\n"
        b"Root-Is-Purelib: true\nTag: py3-none-any\n"
    )
    record = "".join(
        f"{path},sha256={_digest(data)},{len(data)}\n"
        for path, data in contents.items()
    )
    contents[f"{info}/RECORD"] = (record + f"{info}/RECORD,,\n").encode()
    with zipfile.ZipFile(folder / f"{name}-{version}-py3-none-any.whl", "w") as wheel:
        for path, data in contents.items():
            wheel.writestr(path, data)


@pytest.fixture
def env(tmp_path, monkeypatch):
    index = tmp_path / "index"
    index.mkdir()
    for (name, version), spec in WHEELS.items():
        _build_wheel(index, name, version, spec)
    monkeypatch.setenv("PIP_NO_INDEX", "1")
    monkeypatch.setenv("PIP_FIND_LINKS", index.as_uri())  # no spaces
    monkeypatch.setenv(
        "PIP_CONFIG_FILE", "nul" if sys.platform == "win32" else "/dev/null"
    )
    return Env(tmp_path, runner=subprocess.run)  # the real pip


def module(body):
    return f"{body}\n{BASE}class C(Base):\n    pass\n"


def uses_lib(version):
    return module(f"import dashaitestlib\nassert dashaitestlib.VERSION == '{version}'")


def test_dependency_lifecycle_with_real_pip(env):
    marker = env.marker()

    env.install("q", "1.0.0", ["dashaitestextra[fast]"])
    assert env.on_disk() == ["dashaitestextra-1.0", "dashaitestspeed-1.0"]

    env.install("p", "1.0.0", ["dashaitestlib==1.0"], uses_lib("1.0"), cls="C")
    assert "p" not in env.installer.pending_restart

    updated = env.install("p", "2.0.0", ["dashaitestlib>=2"], uses_lib("2.0"), "C")
    assert updated.version == "2.0.0"
    assert "p" in env.installer.pending_restart
    assert "dashaitestlib-2.0" in env.on_disk()
    assert "dashaitestlib-1.0" not in env.on_disk()
    assert not (env.deps_dir / "dashaitestlib_old.py").exists()

    stamp = marker.stat().st_mtime_ns
    env.install("r", "1.0.0", ["dashaitestlib>=1"])
    assert marker.stat().st_mtime_ns == stamp

    with pytest.raises(PluginInstallError):
        env.install(
            "s", "1.0.0", ["dashaitestnew"], module("raise RuntimeError('x')"), "C"
        )
    assert "dashaitestnew-1.0" not in env.on_disk()
    assert not (env.deps_dir / "dashaitestnew.py").exists()

    with pytest.raises(PluginInstallError):
        env.install("t", "1.0.0", ["dashaitestlib<2"])
    assert "dashaitestlib-2.0" in env.on_disk()

    env.installer.uninstall("q")
    env.installer.uninstall("p")
    assert env.on_disk() == ["dashaitestlib-2.0"]  # r still needs it
    env.installer.uninstall("r")
    assert env.on_disk() == []
    assert not (env.deps_dir / "dashaitestlib").exists()
