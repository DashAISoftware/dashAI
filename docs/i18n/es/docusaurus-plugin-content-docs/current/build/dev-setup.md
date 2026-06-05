---
title: Configuración de Desarrollo
sidebar_label: Configuración de Desarrollo
sidebar_position: 2
---

# Configuración de Desarrollo

## Requisitos Previos

- Python 3.10 a 3.13
- Node.js (LTS) y Yarn 3.5.0
- Git

## 1. Clonar el Repositorio

```bash
git clone https://github.com/DashAISoftware/DashAI.git
cd DashAI
git checkout develop
```

## 2. Configuración del Backend

Crea y activa un entorno de Python (conda o venv):

```bash
conda create -n dashai python=3.10
conda activate dashai
```

Instala el paquete en modo editable con las dependencias de desarrollo:

```bash
pip install -r requirements.txt
pip install -e .
pip install -r requirements-dev.txt
pre-commit install
```

## 3. Configuración del Frontend

```bash
cd DashAI/front
yarn install
```

## Ejecutar en Desarrollo

**Backend** (desde la raíz del repositorio):

```bash
python -m DashAI
# o
dashai --no-browser --logging-level INFO
```

**Frontend** (servidor de desarrollo con recarga en caliente):

```bash
cd DashAI/front
yarn start
```

El backend corre en `http://localhost:8000` y el servidor de desarrollo del frontend en `http://localhost:3000`.

## Linting y Formateo

**Python** (usando Ruff):

```bash
ruff check . --fix
ruff format .
```

**Frontend** (ESLint + Prettier):

```bash
cd DashAI/front
yarn lint
```

## Hooks de Pre-commit

dashAI usa hooks de pre-commit para mantener la calidad del código:

```bash
# Ejecutar todos los hooks manualmente
pre-commit run --all-files

# Ejecutar sobre archivos en staging (ocurre automáticamente en git commit)
pre-commit run
```

## Estructura del Proyecto

```
DashAI/
├── DashAI/
│   ├── __main__.py         # Punto de entrada CLI (Typer)
│   ├── back/               # Backend FastAPI
│   │   ├── app.py          # Application factory
│   │   ├── container.py    # Kink DI container
│   │   ├── initial_components.py  # Registro de componentes al iniciar
│   │   ├── api/            # Routers y schemas de request/response
│   │   ├── converters/     # Componentes Converter
│   │   ├── dataloaders/    # Componentes DataLoader
│   │   ├── dependencies/   # Registry, motor de base de datos, cola de jobs
│   │   ├── explainability/ # Componentes Explainer
│   │   ├── exploration/    # Componentes Explorer
│   │   ├── job/            # Implementaciones de Jobs
│   │   ├── metrics/        # Componentes Metric
│   │   ├── models/         # Componentes de modelos ML
│   │   ├── optimizers/     # Componentes optimizadores de hiperparámetros
│   │   ├── plugins/        # Sistema de carga de plugins
│   │   ├── tasks/          # Componentes Task
│   │   └── types/          # Definiciones de tipos compartidos
│   └── front/              # Frontend React
│       └── src/
│           ├── api/        # Cliente HTTP
│           ├── components/ # Componentes de UI
│           └── pages/      # Componentes de páginas
├── docs/                   # Sitio de documentación (Docusaurus)
├── tests/                  # Tests del backend
└── alembic/                # Migraciones de base de datos
```
