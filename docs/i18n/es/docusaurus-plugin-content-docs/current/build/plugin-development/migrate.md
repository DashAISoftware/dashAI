---
title: Migrar un Plugin de PyPI
sidebar_label: Migrar un Plugin de PyPI
---

# Migrar un plugin de PyPI al formato con manifiesto

dashAI ya no descubre paquetes `dashai-*` a través del entry point
`dashai.plugins`. Ahora un plugin es una carpeta con un `manifest.json`, que
se instala desde el módulo **Plugins** como `.zip` subido o desde una release de
GitHub. Tu código Python no cambia: escribe el manifiesto, haz relativos los
imports internos y publica una release.

## Qué se convierte en qué

| Antes (`pyproject.toml`)                  | Ahora (`manifest.json`)                                        |
| ----------------------------------------- | -------------------------------------------------------------- |
| `name`                                    | `"id"` (único) y `"name"` (el que ve el usuario)               |
| `version`, `authors`, `description`       | mismos nombres                                                 |
| `[project.urls]`                          | `"project_urls"`                                               |
| `dependencies`                            | `"dependencies"`                                               |
| `[project.entry-points.'dashai.plugins']` | `"components"` (clase y tipo)                                  |
| `keywords`, prefijo `dashai-`             | ya no hacen falta                                              |
| —                                         | `"manifest_version": "1"` y `"min_app_version"` (obligatorios) |

## Paso 1: Escribir `manifest.json`

Ponlo en la raíz de la carpeta del plugin:

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

- `id`: minúsculas y dígitos separados por un solo `-`. Mantenlo estable,
  porque instalar un id ya instalado lo reemplaza.
- Todo enlace debe ser `http://` o `https://`.
- `min_app_version`: la versión más baja de dashAI con la que funciona.
- `components`: `class` es `modulo:NombreClase`. `type` es uno de `Model`,
  `Converter`, `Metric`, `Task`, `DataLoader`, `Explorer`, `GlobalExplainer`,
  `LocalExplainer`, `GenerativeModel`, `GenerativeTask`, y debe coincidir con la
  clase base. El id de un componente es `<id-del-plugin>:Clase`, que es lo que
  guardan las ejecuciones, así que no renombres clases.
- `dependencies`: especificadores de pip, acotados a las versiones que trae
  dashAI. No incluyas dashAI.
- `plugin_dependencies` y `settings` son opcionales, ver más abajo.

## Paso 2: Hacer relativos los imports internos

dashAI carga cada plugin en su propio espacio de nombres y no lo agrega a
`sys.path`, así que los imports entre tus módulos (en la raíz o en `src/`)
deben ser relativos. La vista previa rechaza uno absoluto y dice qué import
escribir:

```python
from dashai_phi_model_package.utils import download_weights  # rechazado
from .utils import download_weights  # funciona
```

Donde no sirve una sentencia import, nombra tu paquete con `__package__`, por
ejemplo `resources.files(__package__) / "weights.bin"`. Una librería copiada
dentro del plugin cuenta como código tuyo: haz relativos sus imports o
inclúyela en `dependencies`. dashAI ignora `pyproject.toml`.

## Paso 3: Probarlo localmente

Comprime la carpeta (con `manifest.json` en la raíz o en una sola carpeta de
primer nivel) y súbela en **Plugins**. La vista previa muestra los componentes
y cualquier error de validación antes de instalar. Subir una versión nueva con
el mismo `id` la reemplaza sin reiniciar dashAI, salvo que la versión nueva
cambie un paquete pip que ya está cargado.

## Paso 4: Publicar en GitHub

El usuario pega la URL de tu repositorio y dashAI instala la última
release. Adjunta exactamente un `.zip` (o `.tar.gz`) con `manifest.json` en
su raíz; si no, dashAI instala el código fuente del tag. Sube `version` en
cada release, porque **Actualizar** compara versiones.

Una release construida y atestiguada por un workflow obtiene el nivel de
confianza más alto. Agrega `.github/workflows/release.yml`:

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

## Opcional: ajustes

Declara ajustes globales en una subclase de `BasePluginSettings`, con los
mismos tipos de campo que los parámetros de un componente, y nómbrala en el
manifiesto (`"settings": "settings:Settings"`). El usuario los edita en la
pestaña **Configuración** del plugin.

```python
from DashAI.back.core.schema_fields import schema_field, string_field
from DashAI.back.plugins.settings import BasePluginSettings


class Settings(BasePluginSettings):
    url: schema_field(string_field(), "http://localhost:11434", "Server URL")
```

- Llama a `Settings.load()` donde se usa el valor, no al importar, para que un
  cambio llegue al siguiente job.
- El placeholder es el valor por defecto y debe ser válido. No se permiten
  campos `search_space`.
- Los valores se guardan como texto plano, así que nunca pongas secretos.

## Opcional: otros plugins

Lista por id los plugins que el tuyo necesita en `plugin_dependencies` (no en
`dependencies`, que son paquetes de pip) e impórtalos desde
`dashai_plugins.p<id>`, con `-` como `_`:

```python
from dashai_plugins.pplugin_b.base import BaseScorer
```

dashAI carga el tuyo después de ellos y solo mientras estén activos. Instalar
el tuyo también instala desde la tienda los que falten, si dashAI tiene una
(`DASHAI_PLUGIN_INDEX_URL`). Para exigir versiones
compatibles, agrega un rango como `"plugin-b>=1.2,<2"`: dashAI no instala el
tuyo mientras el `plugin-b` instalado quede fuera del rango, y de la tienda toma
la release más nueva dentro de él.

## Niveles de confianza

| Nivel             | Cuándo                                                                           |
| ----------------- | -------------------------------------------------------------------------------- |
| `github_attested` | Archivo de release construido y atestiguado por un workflow del mismo repo y tag |
| `github_source`   | Sin un único archivo de release, el código del repo en el commit del tag         |
| `github_asset`    | Un archivo de release sin atestación válida                                      |
| `local`           | Un `.zip` subido a mano                                                          |

El nivel dice de dónde vienen los archivos, no que el código sea seguro.
