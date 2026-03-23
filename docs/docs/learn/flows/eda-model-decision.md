---
title: "Flow: EDA → Model Decision"
sidebar_label: EDA → Model Decision
sidebar_position: 2
---

# Flow: EDA → Model Decision

This flow demonstrates how thorough Exploratory Data Analysis (EDA) guides modeling decisions. Exploration is not a preliminary formality — it is the foundation for choosing what model to use and how to configure it.

## Objective

Show how the insights from EDA directly determine feature selection, model choice, and split configuration.

## 1. Deep Exploration

Before thinking about models:

- Use **DescribeExplorer** to understand distributions and value ranges
- Use **CorrelationMatrixExplorer** to find redundant or highly correlated variables
- Use **BoxPlotExplorer** to detect outliers
- Use **ScatterPlotExplorer** to visualize relationships between pairs of variables

## 2. EDA-Driven Decisions

What you discover in EDA guides everything else:

| Finding | Action |
|---------|--------|
| Highly correlated variables | Consider removing one to reduce noise |
| Extreme outliers | Consider normalization or removal |
| Imbalanced class distribution | Adjust splits or choose appropriate metrics (F1 over Accuracy) |
| Categorical variables with many categories | Choose encoding strategy |

## 3. Informed Model Selection

With EDA complete, model selection is an informed decision, not a blind search:

- **Linearly separable data** → Logistic Regression may be sufficient
- **Complex non-linear relationships** → Random Forest or SVC
- **Many features** → Consider feature importance after a first training run to prune

:::info
This flow represents the correct way to approach ML: decisions are data-driven. Random model selection without EDA is a common source of poor results.
:::
