---
title: Migrating a PyPI Plugin
sidebar_label: Migrating a PyPI Plugin
---

# Migrating a PyPI plugin to the manifest format

dashAI no longer discovers `dashai-*` packages through the `dashai.plugins`
entry point. A plugin is now a folder with a `manifest.json`, installed from
the **Plugins** module as an uploaded `.zip` or from a GitHub release. Your
Python code stays the same: write the manifest, make internal imports
relative, and publish a release.

## What maps to what

| Old (`pyproject.toml`)                    | New (`manifest.json`)                                        |
| ----------------------------------------- | ------------------------------------------------------------ |
| `name`                                    | `"id"` (unique) and `"name"` (shown to users)                |
| `version`, `authors`, `description`       | same names                                                   |
| `[project.urls]`                          | `"project_urls"`                                             |
| `dependencies`                            | `"dependencies"`                                             |
| `[project.entry-points.'dashai.plugins']` | `"components"` (class and type)                              |
| `keywords`, `dashai-` prefix              | not needed                                                   |
| —                                         | `"manifest_version": "1"` and `"min_app_version"` (required) |

## Step 1: Write `manifest.json`

Put it at the root of the plugin folder:

```json
{
  "manifest_version": "1",
  "id": "phi-model",
  "name": "Phi Model",
  "version": "0.0.2",
  "min_app_version": "0.9.0",
  "description": "Phi Model for dashAI",
  "authors": [
    { "name": "DashAI team", "url": "https://github.com/DashAISoftware" }
  ],
  "project_urls": {
    "Issues": "https://github.com/DashAISoftware/DashAI/issues"
  },
  "components": [
    {
      "class": "dashai_phi_model_package.phi_model:PhiModel",
      "type": "GenerativeModel"
    }
  ],
  "dependencies": ["llama-cpp-python>=0.2.90"]
}
```

- `id`: lowercase letters and digits separated by single `-`. Keep it
  stable, since installing an id that is already installed replaces it.
- Every link must be `http://` or `https://`.
- `min_app_version`: the lowest dashAI your plugin works with.
- `components`: `class` is `module:ClassName`. `type` is one of `Model`,
  `Converter`, `Metric`, `Task`, `DataLoader`, `Explorer`, `GlobalExplainer`,
  `LocalExplainer`, `GenerativeModel`, `GenerativeTask`, and must match the
  base class. A component's id is `<plugin-id>:Class`, which is what saved
  runs refer to, so don't rename classes.
- `dependencies`: pip specifiers, constrained to the versions dashAI ships.
  Don't list dashAI.
- `plugin_dependencies` and `settings` are optional, see below.

## Step 2: Make internal imports relative

dashAI loads each plugin in its own namespace and does not add it to
`sys.path`, so imports between your own modules (at the plugin root or in
`src/`) must be relative. The preview refuses an absolute one and names the
import to write instead:

```python
from dashai_phi_model_package.utils import download_weights  # refused
from .utils import download_weights  # works
```

Where an import statement can't be used, name your package with
`__package__`, for example `resources.files(__package__) / "weights.bin"`.
A vendored library counts as your own code: make its imports relative or list
it in `dependencies`. dashAI ignores `pyproject.toml`.

## Step 3: Try it locally

Zip the folder (with `manifest.json` at the root or in a single top-level
folder) and upload it in **Plugins**. The preview lists the components and any
validation error before installing. Uploading a new version with the same `id`
replaces it without restarting dashAI, unless the new version changes a pip
package that is already loaded.

## Step 4: Publish on GitHub

Users paste your repository URL and dashAI installs the latest release.
Attach exactly one `.zip` (or `.tar.gz`) with `manifest.json` at its root,
otherwise dashAI installs the tag's source code. Raise `version` with every
release, since **Update** compares versions.

A release built and attested by a workflow gets the highest trust level. Add
`.github/workflows/release.yml`:

```yaml
name: Release plugin

on:
  push:
    tags: ["v*"]

permissions:
  contents: write
  id-token: write
  attestations: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Use the tag as the version
        run: jq --arg v "${GITHUB_REF_NAME#v}" '.version = $v' manifest.json > m.json && mv m.json manifest.json
      - name: Build plugin zip
        run: zip -r "my-plugin-${GITHUB_REF_NAME}.zip" manifest.json src README.md LICENSE
      - uses: actions/attest-build-provenance@v2
        with:
          subject-path: my-plugin-${{ github.ref_name }}.zip
      - name: Create the release
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh release create "$GITHUB_REF_NAME" "my-plugin-${GITHUB_REF_NAME}.zip" --title "$GITHUB_REF_NAME"
```

## Optional: settings

Declare global settings in a `BasePluginSettings` subclass, with the same
field types as a component's parameters, and name it in the manifest
(`"settings": "settings:Settings"`). Users edit them in the plugin's
**Settings** tab.

```python
from DashAI.back.core.schema_fields import schema_field, string_field
from DashAI.back.plugins.settings import BasePluginSettings


class Settings(BasePluginSettings):
    url: schema_field(string_field(), "http://localhost:11434", "Server URL")
```

- Call `Settings.load()` where the value is used, not at import time, so a
  change reaches the next job.
- The placeholder is the default and must be valid. `search_space` fields are
  not allowed.
- Values are stored as plain text, so never put secrets there.

## Optional: other plugins

List the plugins yours needs by id in `plugin_dependencies` (not in
`dependencies`, which are pip packages) and import them from
`dashai_plugins.p<id>`, with `-` as `_`:

```python
from dashai_plugins.pplugin_b.base import BaseScorer
```

dashAI loads yours after them and only while they are active. Installing
yours also installs the missing ones from the plugin store, if dashAI has one
(`DASHAI_PLUGIN_INDEX_URL`). To require
compatible releases, add a range such as `"plugin-b>=1.2,<2"`: dashAI refuses
to install yours while the installed `plugin-b` is out of range, and from the
store it takes the newest release in range.

## Trust levels

| Level             | When                                                                   |
| ----------------- | ---------------------------------------------------------------------- |
| `github_attested` | Release file built and attested by a workflow of the same repo and tag |
| `github_source`   | No single release file, the repo's code at the tag's commit            |
| `github_asset`    | A release file without a valid attestation                             |
| `local`           | A `.zip` uploaded by hand                                              |

The level says where the files came from, not that the code is safe.
