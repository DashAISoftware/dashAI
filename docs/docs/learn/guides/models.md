---
title: "Module Guide: Models"
sidebar_label: Models
sidebar_position: 2
---

# Module Guide: Models

The Models module manages the full ML experimentation cycle: from creating experiments to training, evaluating, and comparing models.

## Creating an Experiment

An experiment requires:

1. A descriptive name
2. A **Task** (Tabular Classification, Text Classification, Regression, etc.)
3. An associated **Dataset**
4. Feature (input) and target (output) column configuration
5. Data splits (train / validation / test ratios)

Internally this creates a **Model Session** in the database, which tracks all associated runs.

## Available Models

DashAI includes models from multiple frameworks:

### Scikit-learn
| Model | Task |
|-------|------|
| SVC | Tabular Classification |
| LogisticRegression | Tabular Classification |
| RandomForestClassifier | Tabular Classification |
| DecisionTreeClassifier | Tabular Classification |
| KNeighborsClassifier | Tabular Classification |
| HistGradientBoostingClassifier | Tabular Classification |
| DummyClassifier | Tabular Classification |
| LinearRegression | Regression |
| LinearSVR | Regression |
| RidgeRegression | Regression |
| RandomForestRegression | Regression |
| GradientBoostingR | Regression |
| MLPRegression | Regression |

### Hugging Face Transformers
| Model | Task |
|-------|------|
| DistilBertTransformer | Text Classification |
| BagOfWordsTextClassificationModel | Text Classification |
| OpusMtEnESTransformer | Translation |

## Comparing Runs

Within an experiment you can:

- Train multiple models with different configurations
- Compare metrics across runs (Accuracy, F1, RMSE, etc.)
- Identify the best model for your specific task
- Run automatic hyperparameter optimization

## Hyperparameter Optimization

Two optimizers are available:

- **OptunaOptimizer** — Bayesian optimization using Optuna
- **HyperOptOptimizer** — Tree-structured Parzen Estimator (TPE) search

During optimization, DashAI records per-trial metrics and generates visualization plots (history, parallel coordinates, slice, importance).

## Explainability

DashAI includes explainability tools compatible with tabular classification and regression:

- **Kernel SHAP** — Contribution of each feature to individual predictions
- **Permutation Feature Importance** — Feature ranking via permutation
- **Partial Dependence** — Relationship between features and model output

:::info
Explainability helps you understand *why* a model makes certain decisions, not just how accurate it is.
:::
