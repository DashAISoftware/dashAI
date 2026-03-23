---
title: Installation
sidebar_label: Installation
---

# Installation

## Requirements

DashAI requires **Python 3.10 or greater**.

## Quick Install (PyPI)

Install DashAI via pip:

```bash
pip install dashai
```

Then start the server and graphical interface:

```bash
dashai
```

Go to [http://localhost:3000/](http://localhost:3000/) in your browser to access the DashAI graphical interface.

### Optional Flags

**Set the local data path** (where DashAI saves datasets, runs, and other files):

```bash
python -m DashAI --local-path "~/.DashAI"
```

**Set the logging level** (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`):

```bash
python -m DashAI --logging-level INFO
```

**Disable automatic browser opening:**

```bash
python -m DashAI --no-browser
```

**View all available options:**

```bash
python -m DashAI --help
```

## Development Install

To set up DashAI for local development:

### 1. Clone the repository

```bash
git clone https://github.com/DashAISoftware/DashAI.git
cd DashAI
git checkout develop
```

### 2. Install backend dependencies

Create and activate a Python environment (conda or venv recommended):

```bash
conda create -n dashai python=3.10
conda activate dashai
```

Install the package in editable mode along with development dependencies:

```bash
pip install -e .
pip install -r requirements-dev.txt
pre-commit install
```

### 3. Install frontend dependencies

Node.js (LTS) and Yarn 3.5.0 are required.

```bash
cd DashAI/front
yarn install
```

## Running the Application

**Run as a module (recommended during development):**

```bash
python -m DashAI
```

**Or use the installed CLI entry point:**

```bash
dashai --no-browser --logging-level INFO
```

**Run only the frontend development server:**

```bash
cd DashAI/front
yarn start
```

## Running Tests

### Backend tests

DashAI uses [pytest](https://docs.pytest.org/) for backend testing.

Run all backend tests:

```bash
pytest -v
```

Run a single test file:

```bash
pytest tests/back/api/test_components_api.py -v
```

Run a single test by name:

```bash
pytest tests/back/api/test_components_api.py::test_name -v
```

### Frontend tests

```bash
cd DashAI/front
yarn test
```

## Database Migrations

Migrations are managed through [Alembic](https://alembic.sqlalchemy.org/en/latest/) and run automatically on startup. To run them manually (from the `DashAI/` folder):

```bash
alembic upgrade head
```

**Create a new migration** after modifying database models:

```bash
alembic revision --autogenerate -m "description of changes"
```

Generated migrations are saved in `alembic/versions/` and must be committed to the repository.

**Downgrade one step:**

```bash
alembic downgrade -1
```

**Check current migration status:**

```bash
alembic current
```

## Test Datasets

Sample datasets for trying DashAI are available at the [DashAI_Datasets repository](https://github.com/DashAISoftware/DashAI_Datasets).
