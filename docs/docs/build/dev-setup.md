---
title: Development Setup
sidebar_label: Development Setup
sidebar_position: 2
---

# Development Setup

## Prerequisites

- Python 3.10 or greater
- Node.js (LTS) and Yarn 3.5.0
- Git

## 1. Clone the Repository

```bash
git clone https://github.com/DashAISoftware/DashAI.git
cd DashAI
git checkout develop
```

## 2. Backend Setup

Create and activate a Python environment (conda or venv):

```bash
conda create -n dashai python=3.10
conda activate dashai
```

Install the package in editable mode with development dependencies:

```bash
pip install -e .
pip install -r requirements-dev.txt
pre-commit install
```

## 3. Frontend Setup

```bash
cd DashAI/front
yarn install
```

## Running in Development

**Backend** (from the repo root):

```bash
python -m DashAI
# or
dashai --no-browser --logging-level INFO
```

**Frontend** (development server with hot reload):

```bash
cd DashAI/front
yarn start
```

The backend runs at `http://localhost:8000` and the frontend dev server at `http://localhost:3000`.

## Linting and Formatting

**Python** (using Ruff):

```bash
ruff check . --fix
ruff format .
```

**Frontend** (ESLint + Prettier):

```bash
cd DashAI/front
yarn lint
```

## Pre-commit Hooks

DashAI uses pre-commit hooks for consistent code quality:

```bash
# Run all hooks manually
pre-commit run --all-files

# Run on staged files (happens automatically on git commit)
pre-commit run
```

## Project Structure

```
DashAI/
├── DashAI/
│   ├── __main__.py         # CLI entry point (Typer)
│   ├── back/               # FastAPI backend
│   │   ├── app.py          # Application factory
│   │   ├── api/            # Routers and schemas
│   │   ├── models/         # ML model components
│   │   ├── tasks/          # Task components
│   │   ├── metrics/        # Metric components
│   │   ├── explorers/      # Explorer components (in back/exploration/)
│   │   ├── converters/     # Converter components
│   │   ├── explainability/ # Explainer components
│   │   ├── job/            # Job implementations
│   │   ├── dependencies/   # Registry, database, job queue
│   │   └── container.py    # Kink DI container
│   └── front/              # React frontend
│       └── src/
│           ├── api/        # HTTP client
│           ├── components/ # UI components
│           └── pages/      # Page components
├── docs/                   # Documentation site (Docusaurus)
├── tests/                  # Backend tests
└── alembic/                # Database migrations
```
