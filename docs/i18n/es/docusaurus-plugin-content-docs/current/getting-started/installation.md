---
title: Instalación
sidebar_label: Instalación
---

# Instalación

## Requisitos

DashAI requiere **Python 3.10 o superior**.

## Instalación Rápida (PyPI)

Instala DashAI mediante pip:

```bash
pip install dashai
```

Luego inicia el servidor y la interfaz gráfica:

```bash
dashai
```

Accede a la interfaz gráfica de DashAI en tu navegador en [http://localhost:3000/](http://localhost:3000/).

### Opciones Adicionales

**Establecer la ruta de datos local** (donde DashAI guarda conjuntos de datos, ejecuciones y otros archivos):

```bash
python -m DashAI --local-path "~/.DashAI"
```

**Establecer el nivel de registro** (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`):

```bash
python -m DashAI --logging-level INFO
```

**Deshabilitar la apertura automática del navegador:**

```bash
python -m DashAI --no-browser
```

**Ver todas las opciones disponibles:**

```bash
python -m DashAI --help
```

## Instalación para Desarrollo

Para configurar DashAI para desarrollo local:

### 1. Clonar el repositorio

```bash
git clone https://github.com/DashAISoftware/DashAI.git
cd DashAI
git checkout develop
```

### 2. Instalar las dependencias del backend

Crea y activa un entorno Python (se recomienda conda o venv):

```bash
conda create -n dashai python=3.10
conda activate dashai
```

Instala el paquete en modo editable junto con las dependencias de desarrollo:

```bash
pip install -e .
pip install -r requirements-dev.txt
pre-commit install
```

### 3. Instalar las dependencias del frontend

Se requieren Node.js (LTS) y Yarn 3.5.0.

```bash
cd DashAI/front
yarn install
```

## Ejecutar la Aplicación

**Ejecutar como módulo (recomendado durante el desarrollo):**

```bash
python -m DashAI
```

**O usar el punto de entrada CLI instalado:**

```bash
dashai --no-browser --logging-level INFO
```

**Ejecutar solo el servidor de desarrollo del frontend:**

```bash
cd DashAI/front
yarn start
```

## Ejecutar Tests

### Tests del backend

DashAI usa [pytest](https://docs.pytest.org/) para las pruebas del backend.

Ejecutar todos los tests del backend:

```bash
pytest -v
```

Ejecutar un único archivo de tests:

```bash
pytest tests/back/api/test_components_api.py -v
```

Ejecutar un test específico por nombre:

```bash
pytest tests/back/api/test_components_api.py::test_name -v
```

### Tests del frontend

```bash
cd DashAI/front
yarn test
```

## Migraciones de Base de Datos

Las migraciones se gestionan a través de [Alembic](https://alembic.sqlalchemy.org/en/latest/) y se ejecutan automáticamente al iniciar. Para ejecutarlas manualmente (desde la carpeta `DashAI/`):

```bash
alembic upgrade head
```

**Crear una nueva migración** después de modificar los modelos de la base de datos:

```bash
alembic revision --autogenerate -m "description of changes"
```

Las migraciones generadas se guardan en `alembic/versions/` y deben confirmarse en el repositorio.

**Revertir un paso:**

```bash
alembic downgrade -1
```

**Verificar el estado actual de la migración:**

```bash
alembic current
```

## Conjuntos de Datos de Prueba

Se dispone de conjuntos de datos de ejemplo para probar DashAI en el [repositorio DashAI_Datasets](https://github.com/DashAISoftware/DashAI_Datasets).
