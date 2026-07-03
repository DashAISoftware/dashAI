---
title: Development Setup
sidebar_label: Development Setup
sidebar_position: 2
---

# Development Setup

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (manages Python and dependencies; Python 3.10 to 3.13)
- Node.js (LTS) and Yarn 3.5.0
- Git

## 1. Clone the Repository

```bash
git clone https://github.com/DashAISoftware/DashAI.git
cd DashAI
git checkout develop
```

## 2. Backend Setup

Install all dependencies (uv creates the `.venv` and installs the package
in editable mode, including development dependencies):

```bash
uv sync
uv run pre-commit install
```

On machines without an NVIDIA GPU you can use the CPU-only PyTorch wheels,
which are much lighter:

```bash
uv sync --extra cpu
```

## 3. Frontend Setup

```bash
cd DashAI/front
yarn install
```

## Running in Development

**Backend** (from the repo root):

```bash
uv run python -m DashAI
# or
uv run dashai --no-browser --logging-level INFO
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
uv run ruff check . --fix
uv run ruff format .
```

**Frontend** (ESLint + Prettier):

```bash
cd DashAI/front
yarn lint
```

## Pre-commit Hooks

dashAI uses pre-commit hooks for consistent code quality:

```bash
# Run all hooks manually
uv run pre-commit run --all-files

# Run on staged files (happens automatically on git commit)
uv run pre-commit run
```

## Project Structure

```
DashAI/
├── DashAI/
│   ├── __main__.py         # CLI entry point (Typer)
│   ├── back/               # FastAPI backend
│   │   ├── app.py          # Application factory
│   │   ├── container.py    # Kink DI container
│   │   ├── initial_components.py  # Startup component registration
│   │   ├── api/            # Routers and request/response schemas
│   │   ├── converters/     # Converter components
│   │   ├── dataloaders/    # DataLoader components
│   │   ├── dependencies/   # Registry, database engine, job queue
│   │   ├── explainability/ # Explainer components
│   │   ├── exploration/    # Explorer components
│   │   ├── job/            # Job implementations
│   │   ├── metrics/        # Metric components
│   │   ├── models/         # ML model components
│   │   ├── optimizers/     # Hyperparameter optimizer components
│   │   ├── plugins/        # Plugin loading system
│   │   ├── tasks/          # Task components
│   │   └── types/          # Shared type definitions
│   └── front/              # React frontend
│       └── src/
│           ├── api/        # HTTP client
│           ├── components/ # UI components
│           └── pages/      # Page components
├── docs/                   # Documentation site (Docusaurus)
├── tests/                  # Backend tests
└── alembic/                # Database migrations
```
