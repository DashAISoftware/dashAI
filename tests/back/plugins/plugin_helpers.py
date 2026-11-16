"""Shared plugin test helpers, builders, a fake pip and GitHub, a real installer."""

import io
import json
import subprocess
import zipfile
from contextlib import contextmanager
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.plugins.dependencies import PluginDependencies, activate_dependencies
from DashAI.back.plugins.disk.storage import PluginStorage
from DashAI.back.plugins.plugin_installer import WORKER_RESTART_MARKER, PluginInstaller
from DashAI.back.plugins.sources.github_source import GitHubSource
from DashAI.back.plugins.sources.local_source import LocalSource
from DashAI.back.plugins.store.store import INDEX_FILE

URL = "https://github.com/owner/repo"
BASE = "class Base:\n    TYPE = 'Converter'\n\n"
BROKEN = BASE + "class {cls}(Base):\n    pass\n\nraise RuntimeError('broken')\n"


def module(cls, body="pass"):
    """A module defining ``cls``, a component of its own ``Base``."""
    return f"{BASE}class {cls}(Base):\n    {body}\n"


def manifest(plugin_id="my-plugin", cls="C", **fields):
    """A valid manifest with one Converter, ``mod:<cls>``."""
    return {
        "manifest_version": "1",
        "id": plugin_id,
        "name": plugin_id,
        "authors": [{"name": "t"}],
        "version": "1.0.0",
        "min_app_version": "0.0.1",
        "components": [{"class": f"mod:{cls}", "type": "Converter"}],
        **fields,
    }


def make_plugin(folder, plugin_id="my-plugin", cls="C", code=None, **fields):
    """A plugin folder with ``mod.py`` and its manifest (``fields`` override it)."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "mod.py").write_text(code or module(cls), encoding="utf-8")
    (folder / "manifest.json").write_text(
        json.dumps(manifest(plugin_id, cls, **fields)), encoding="utf-8"
    )
    return folder


def zip_bytes(files, wrap_in=None):
    """An in-memory .zip of ``{name: text or bytes}``, optionally in one folder."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(f"{wrap_in}/{name}" if wrap_in else name, content)
    return buffer.getvalue()


def plugin_zip(plugin_id="my-plugin", cls="C", code=None, **fields):
    """A plugin as an uploaded .zip."""
    files = {"manifest.json": json.dumps(manifest(plugin_id, cls, **fields))}
    return zip_bytes({**files, "mod.py": code or module(cls)})


def fake_installed(storage, plugin_id, location=None, ref="v1.0.0", source="git"):
    """A plugin folder with only its markers, as the store and updates read it."""
    folder = storage.plugin_dir(plugin_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text("{}", encoding="utf-8")
    default = f"https://github.com/acme/{plugin_id}"
    location = location or (default if source == "git" else f"{plugin_id}.zip")
    (folder / ".source").write_text(
        json.dumps({"source": source, "location": location, "ref": ref}),
        encoding="utf-8",
    )


SHA = "a" * 64
COMMIT = "c" * 40


def release(tag, app="0.0.1", level="github_attested"):
    return {
        "tag": tag,
        "version": tag.lstrip("v"),
        "min_app_version": app,
        "trust_level": level,
        "sha256": SHA,
        "commit": COMMIT,
        "published_at": "2026-10-08T15:18:18Z",
        "dependencies": [],
    }


def entry(plugin_id, releases=None, repo=None, **fields):
    return {
        "id": plugin_id,
        "source": "git",
        "location": f"https://github.com/{repo or 'acme/' + plugin_id}",
        "name": plugin_id.title(),
        "releases": [release("v1.0.0")] if releases is None else releases,
        **fields,
    }


def save_store(storage, plugins=(), removed=(), revoked=()):
    """The store's copy of its index, as if just read."""
    index = {
        "schema": 1,
        "built_at": "2026-10-26T00:00:00+00:00",
        "plugins": list(plugins),
        "removed": list(removed),
        "revoked": list(revoked),
    }
    (storage.root / INDEX_FILE).write_text(json.dumps(index))


INDEX = {
    "a": {"1.0": {}},
    "b": {"1.0": {}},
    "x": {"1.0": {"requires": ["y>=1"]}},
    "y": {"1.0": {}},
    "pkg": {"1.0": {}, "2.0": {}},
    "libx": {
        "1.0": {"files": {"libx.py": "VERSION = '1.0'\n"}},
        "2.0": {
            "files": {"libx.py": "VERSION = '2.0'\n\ndef algo_nuevo():\n    return 1\n"}
        },
    },
}


class FakePip:
    def __init__(self, index, plugins_dir=None):
        """``index`` maps name -> version -> requires and files (default a .py)."""
        self.index = {
            canonicalize_name(name): versions for name, versions in index.items()
        }
        self.plugins_dir = Path(plugins_dir) if plugins_dir else None
        self.calls = []
        self.constraint_contents = []
        self.fail_install = None  # set to a message to make --target installs fail

    def _installed(self):
        found = {}
        if self.plugins_dir is None or not self.plugins_dir.is_dir():
            return found
        for info in self.plugins_dir.glob("*.dist-info"):
            name, version = info.name[: -len(".dist-info")].rsplit("-", 1)
            found[canonicalize_name(name)] = version
        return found

    def files_of(self, name, version):
        entry = self.index[canonicalize_name(name)][version]
        module = canonicalize_name(name).replace("-", "_")
        return entry.get("files") or {f"{module}.py": f"VERSION = '{version}'\n"}

    def _fail(self, cmd, message):
        return subprocess.CompletedProcess(cmd, 1, "", f"ERROR: {message}")

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if "--report" in cmd:
            return self._dry_run(cmd)
        if "--target" in cmd:
            return self._install(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def _dry_run(self, cmd):
        text = Path(cmd[cmd.index("--constraint") + 1]).read_text(encoding="utf-8")
        self.constraint_contents.append(text)
        constraints = []
        for line in filter(None, (raw.strip() for raw in text.splitlines())):
            requirement = Requirement(line)
            if requirement.extras:
                return self._fail(cmd, "Constraints cannot have extras")
            if requirement.url:
                return self._fail(cmd, "Links are not allowed as constraints")
            constraints.append(requirement)
        pinned = {
            canonicalize_name(c.name)
            for c in constraints
            if str(c.specifier).startswith("==")
            and canonicalize_name(c.name) not in self.index
        }
        chosen = {}
        installed = self._installed()
        pending = [Requirement(d) for d in cmd[cmd.index("--") + 1 :]]
        while pending:
            requirement = pending.pop()
            name = canonicalize_name(requirement.name)
            if name in pinned:
                continue  # provided by dashAI
            if name not in self.index:
                return self._fail(cmd, f"No matching distribution found for {name}")
            candidates = [
                v
                for v in self.index[name]
                if requirement.specifier.contains(v, prereleases=True)
                and all(
                    c.specifier.contains(v, prereleases=True)
                    for c in constraints
                    if canonicalize_name(c.name) == name
                )
            ]
            if name in chosen:
                if chosen[name] not in candidates:
                    return self._fail(cmd, f"ResolutionImpossible: {requirement}")
                continue
            if not candidates:
                return self._fail(cmd, f"ResolutionImpossible: {requirement}")
            chosen[name] = (
                installed[name]
                if installed.get(name) in candidates
                else max(candidates, key=Version)
            )
            for child in self.index[name][chosen[name]].get("requires", []):
                child_requirement = Requirement(child)
                marker = child_requirement.marker
                environments = [{"extra": e} for e in requirement.extras] or [
                    {"extra": ""}
                ]
                if marker is None or any(marker.evaluate(e) for e in environments):
                    pending.append(child_requirement)
        report = [
            {
                "metadata": {"name": name, "version": version},
                "download_info": {"url": f"https://pypi.invalid/{name}-{version}.whl"},
            }
            for name, version in sorted(chosen.items())
            if installed.get(name) != version
        ]
        Path(cmd[cmd.index("--report") + 1]).write_text(
            json.dumps({"install": report}), encoding="utf-8"
        )
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def _install(self, cmd):
        if self.fail_install:
            return self._fail(cmd, self.fail_install)
        target = Path(cmd[cmd.index("--target") + 1])
        for url in cmd[cmd.index("--") + 1 :]:
            name, version = url.rsplit("/", 1)[-1][: -len(".whl")].rsplit("-", 1)
            files = self.files_of(name, version)
            for relative, content in files.items():
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            info = target / f"{name}-{version}.dist-info"
            info.mkdir(parents=True, exist_ok=True)
            requires = self.index[name][version].get("requires", [])
            (info / "METADATA").write_text(
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
                + "".join(f"Requires-Dist: {r}\n" for r in requires),
                encoding="utf-8",
            )
            (info / "RECORD").write_text(
                "".join(f"{relative},,\n" for relative in files)
                + f"{info.name}/METADATA,,\n{info.name}/RECORD,,\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(cmd, 0, "", "")


class FakeGitHub(GitHubSource):
    """GitHub without network, ``fetch`` yields ``folder``, ``tags`` the latest."""

    def __init__(self, folder=None, used_asset=False, attested=False, tags=None):
        self.folder, self.used_asset, self.attested = folder, used_asset, attested
        self.tags = tags or {}
        self.calls = []  # fetch adds its url, latest_tag (url, etag)

    @contextmanager
    def fetch(self, url, ref=None):
        self.calls.append(url)
        owner, _repo = self.parse(url)
        yield self._fetched(
            self.folder,
            owner,
            ref or "v1.0.0-fake-latest",
            "f" * 64,
            asset="plugin.zip" if self.used_asset else None,
            attestation=(
                {
                    "commit": "c" * 40,
                    "workflow": ".github/workflows/release.yml",
                    "signed_at": "2026-06-02T10:08:00+00:00",
                }
                if self.attested
                else None
            ),
            commit=None if self.used_asset and not self.attested else "c" * 40,
        )

    def latest_tag(self, url, etag=None):
        self.calls.append((url, etag))
        answer = self.tags[url]
        if isinstance(answer, Exception):
            raise answer
        if answer == etag:  # unchanged, GitHub's 304
            return None, etag
        return answer, answer


class Env:
    """A real installer on ``tmp_path`` with the fake pip and GitHub."""

    def __init__(self, tmp_path, runner=None, load_check=None):
        self.tmp = tmp_path
        self.storage = PluginStorage.at(tmp_path)
        self.deps_dir = activate_dependencies(self.storage.root)
        self.pip = FakePip(INDEX, plugins_dir=self.deps_dir)
        self.registry = ComponentRegistry(initial_components=[])
        self.deps = PluginDependencies(
            local_path=tmp_path, runner=runner or self.pip, index_reachable=lambda: True
        )
        self.github = FakeGitHub()
        self.running = False  # whether a job runs
        self.installer = self.new_installer(load_check=load_check)
        self._count = 0

    def new_installer(self, registry=None, load_check=None):
        """Another installer on the same disk, as reopening dashAI makes."""
        return PluginInstaller(
            self.storage,
            registry or self.registry,
            self.deps,
            sources={PluginSource.LOCAL: LocalSource(), PluginSource.GIT: self.github},
            jobs_running=lambda: self.running,
            load_check=load_check,
        )

    def reopen(self, registry=None):
        """What reopening dashAI does before loading plugins."""
        installer = self.new_installer(registry)
        installer.startup_maintenance()
        return installer

    def plugin(self, plugin_id, version="1.0.0", deps=(), module=None, cls=None, **f):
        """A new source folder of ``plugin_id``."""
        self._count += 1
        folder = self.tmp / f"src-{plugin_id}-{self._count}"
        cls = cls or f"C_{plugin_id.replace('-', '_')}"
        fields = {"version": version, "dependencies": list(deps), **f}
        return str(make_plugin(folder, plugin_id, cls, module, **fields))

    def install(self, *args, **kwargs):
        return self.installer.install(PluginSource.LOCAL, self.plugin(*args, **kwargs))

    def install_git(self, plugin_id="my-plugin", url=URL, **kwargs):
        """``plugin_id`` from GitHub: the next releases go to ``github.folder``."""
        self.github.folder = Path(self.plugin(plugin_id, **kwargs))
        return self.installer.install(PluginSource.GIT, url)

    def update(self, plugin_id="my-plugin", url=URL):
        """As the front does: preview the latest release, then update to it."""
        preview = self.installer.validate(PluginSource.GIT, url).preview
        return self.installer.update(plugin_id, preview)

    def on_disk(self):
        return sorted(
            p.name[: -len(".dist-info")] for p in self.deps_dir.glob("*.dist-info")
        )

    def marker(self):
        return self.storage.root / WORKER_RESTART_MARKER
