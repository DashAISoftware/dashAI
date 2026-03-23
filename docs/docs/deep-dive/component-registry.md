---
title: Component Registry
sidebar_label: Component Registry
sidebar_position: 2
---

# Component Registry

The **Component Registry** is DashAI's centralized catalog of all available ML components. It is the single source of truth for component discovery, configuration, and filtering.

## What is a Component?

Everything pluggable in DashAI is a **component** — models, tasks, metrics, explorers, explainers, converters, data loaders, optimizers, and jobs. Each component:

- Inherits from a typed base class with a `TYPE` class attribute (e.g., `"Model"`, `"Task"`, `"Metric"`)
- Optionally defines a `SCHEMA` (Pydantic model) making it a **Configurable Object**
- Can declare `COMPATIBLE_COMPONENTS` to restrict which other components it works with

## Component Types

| TYPE | Base class | Purpose | Examples |
|------|-----------|---------|---------|
| `Model` | `BaseModel` | Train and predict | SVC, RandomForest, DistilBertTransformer |
| `Task` | `BaseTask` | Define ML task semantics | TextClassification, Regression, Translation |
| `Metric` | `BaseMetric` | Evaluate model performance | Accuracy, F1, RMSE |
| `Explorer` | `BaseExplorer` | Visualize and analyze data | ScatterPlotExplorer, BoxPlotExplorer |
| `Explainer` | `BaseExplainer` | Interpret model predictions | KernelShap, PermutationFeatureImportance |
| `Converter` | `BaseConverter` | Transform features | StandardScaler, OneHotEncoder, PCA |
| `DataLoader` | `BaseDataLoader` | Load datasets from files | CSVDataLoader, ExcelDataLoader |
| `Optimizer` | `BaseOptimizer` | Hyperparameter search | OptunaOptimizer, HyperOptOptimizer |
| `Job` | `BaseJob` | Background task execution | ModelJob, ExplorerJob, PredictJob |

## Registration

The list of components registered at startup is defined in `back/initial_components.py`. At startup, for each component class the registry:

1. Reads the `TYPE` attribute to determine the component category
2. Checks whether the class is a Configurable Object (has `get_schema()`)
3. Extracts metadata: `DESCRIPTION`, `DISPLAY_NAME`, `COLOR`, `COMPATIBLE_COMPONENTS`
4. Stores the component in a dictionary keyed by type and name

Each registered component is stored as:

```python
{
    "name": "SVC",
    "type": "Model",
    "class": SVCClass,
    "configurable_object": True,
    "schema": { ... },        # JSON Schema if configurable
    "metadata": { ... },
    "description": MultilingualString(...),
    "display_name": MultilingualString(...),
    "color": "#3498db",
}
```

## Configurable Objects

Any component that declares a `SCHEMA` class attribute (a Pydantic model) is a **Configurable Object**. Its `get_schema()` method converts the Pydantic model to JSON Schema, which the frontend uses to dynamically render a configuration form.

When a user submits configuration, the backend validates and transforms the parameters using `validate_and_transform()`. This also resolves any nested component references — a parameter of type `ComponentType` is instantiated as the selected component.

## Lookup Methods

| Method | Description |
|--------|-------------|
| `registry[name]` | Direct lookup by component name |
| `get_components_by_types(select, ignore)` | Filter by TYPE |
| `get_child_components(parent_name)` | Components inheriting from a given parent |
| `get_related_components(component_id)` | Compatible components via `COMPATIBLE_COMPONENTS` |

## Multilingual Support

Component metadata is stored as `MultilingualString` objects. The API filters descriptions and display names based on the `Accept-Language` request header, returning content in the user's preferred language.

## Runtime Extension via Plugins

Plugins can register additional components at runtime through the plugin system. This is how third-party models, converters, and other components are added without modifying the core codebase.
