---
title: "Flow: Tabular Classification"
sidebar_label: Tabular Classification
sidebar_position: 1
---

# Flow: Tabular Classification

This flow walks through a complete tabular classification workflow end-to-end — from loading data to making predictions — using the Iris dataset as an example.

## Objective

Train and compare multiple classifiers on the Iris dataset. Select the best-performing model and use it to predict on new data.

## 1. Load and Explore Data

Load the Iris dataset (CSV). Use the **DescribeExplorer** to see basic statistics and the **BoxPlotExplorer** to identify distributions and outliers. Verify that columns are the correct data types.

:::tip
Always explore before modeling. Understanding your data distribution prevents surprises during training.
:::

## 2. Prepare Data

The Iris dataset is already clean. In a real-world case, you would use converters to:

- Normalize numeric features (StandardScaler, MinMaxScaler)
- Encode categorical variables (OneHotEncoder, OrdinalEncoder)
- Handle missing values (SimpleImputer, NanRemover)

## 3. Create a Comparative Experiment

Create an experiment with task **Tabular Classification**. Add three models: **SVC**, **Random Forest**, and **Logistic Regression**. Train all with default parameters to establish a baseline.

## 4. Evaluate and Select

Compare Accuracy and F1-Score across the three models. Use the explainability module to understand which features are most important. Select the model with the best balance of metrics.

## 5. Predict

With the selected model, create a prediction on new data. Review and download the results.

:::tip
This flow is the baseline pattern for any tabular classification task. The key is always: explore first, then model.
:::
