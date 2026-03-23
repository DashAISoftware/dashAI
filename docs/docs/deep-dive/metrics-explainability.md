---
title: Metrics & Explainability
sidebar_label: Metrics & Explainability
sidebar_position: 3
---

# Metrics & Explainability

## Classification Metrics

| Metric | Description |
|--------|-------------|
| **Accuracy** | Proportion of correct predictions over total predictions |
| **F1** | Harmonic mean of Precision and Recall — useful for imbalanced classes |
| **Precision** | Of all predicted positives, how many are actually positive |
| **Recall** | Of all actual positives, how many did the model detect |
| **ROC-AUC** | Area under the ROC curve — measures ranking quality |
| **Log Loss** | Cross-entropy loss — penalizes confident wrong predictions |
| **Cohen's Kappa** | Agreement between predictions and labels, adjusted for chance |
| **Hamming Distance** | Proportion of incorrectly predicted labels |

## Regression Metrics

| Metric | Description |
|--------|-------------|
| **RMSE** | Root Mean Squared Error — error in the same units as the target |
| **MAE** | Mean Absolute Error — less sensitive to outliers than RMSE |
| **MSE** | Mean Squared Error — amplifies large errors |
| **R²** | Proportion of variance explained by the model (1.0 = perfect) |
| **Explained Variance** | Similar to R² but does not penalize systematic bias |
| **Median Absolute Error** | Robust error metric, ignores outliers entirely |

## Translation Metrics

| Metric | Description |
|--------|-------------|
| **BLEU** | Measures n-gram overlap with reference translations |
| **TER** | Translation Edit Rate — edit distance to reference |
| **ChrF** | Character n-gram F-score — works well for morphologically rich languages |

## Metric Tracking

DashAI records metrics at multiple granularities:

| Level | When used |
|-------|-----------|
| `LAST` | Final metric value after training |
| `STEP` | Per training step (e.g., per epoch) |
| `BATCH` | Per mini-batch |
| `TRIAL` | Per optimization trial (hyperparameter search) |

This enables training curves and optimization history plots in the UI.

---

## Explainability

DashAI includes two families of explainability tools.

### Local Explainers

Explain individual predictions.

#### Kernel SHAP

**KernelShap** (`back/explainability/explainers/`) uses SHAP (SHapley Additive exPlanations) to compute the contribution of each feature to each individual prediction.

- **Scope:** Local (per prediction)
- **Compatible tasks:** Tabular Classification, Regression
- **Output:** Feature contribution values per instance

SHAP values are grounded in cooperative game theory: each feature's contribution is the average marginal contribution across all possible feature coalitions.

### Global Explainers

Explain model behavior across the entire dataset.

#### Permutation Feature Importance

**PermutationFeatureImportance** measures the importance of each feature by permuting its values and observing how much the model's performance degrades.

- **Scope:** Global (entire dataset)
- **Compatible tasks:** Tabular Classification, Regression
- **Output:** Importance score per feature

If performance drops significantly when a feature is permuted, that feature is important. If performance is unchanged, the feature is not contributing.

#### Partial Dependence

**PartialDependence** shows the marginal effect of one or two features on the model's predicted outcome, averaging over all other features.

- **Scope:** Global (marginal effect)
- **Compatible tasks:** Tabular Classification, Regression
- **Output:** Partial dependence plots per selected feature
