"""Load a plugin in a fresh interpreter, exit 3 with a failing dependency's id."""

import sys
from pathlib import Path


def main(argv) -> int:
    if len(argv) != 3:
        print(
            "usage: python -m DashAI.back.plugins.load_check <plugin_dir> <local_path>",
            file=sys.stderr,
        )
        return 2
    plugin_dir, local_path = Path(argv[1]), argv[2]

    from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
    from DashAI.back.plugins.bootstrap import install_order
    from DashAI.back.plugins.dependencies import activate_dependencies
    from DashAI.back.plugins.disk.storage import PluginStorage
    from DashAI.back.plugins.loader import PluginLoader
    from DashAI.back.plugins.manifest.manifest import ManifestError, PluginManifest

    storage = PluginStorage.at(local_path)
    activate_dependencies(storage.root)
    registry = ComponentRegistry(initial_components=[])
    try:
        manifest = PluginManifest.from_file(plugin_dir / "manifest.json")
        # Its installed, unblocked dependencies load first, others fail its import
        needed, todo = {}, list(manifest.plugin_dependencies)
        while todo:
            dep = todo.pop()
            if dep in needed or dep == manifest.id or storage.is_blocked(dep):
                continue
            try:
                needed[dep] = PluginManifest.from_file(
                    storage.plugin_dir(dep) / storage.MANIFEST_FILENAME
                )
            except (OSError, ManifestError):
                continue
            todo += needed[dep].plugin_dependencies
        for dep in install_order(needed):
            try:
                PluginLoader.load(needed[dep], storage.plugin_dir(dep), registry)
            except Exception as error:  # noqa: BLE001 - its fault, not the plugin's
                print(dep)
                print(str(error), file=sys.stderr)
                return 3
        PluginLoader.load(manifest, plugin_dir, registry)
    except Exception as error:  # noqa: BLE001 - the verdict is the message
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
