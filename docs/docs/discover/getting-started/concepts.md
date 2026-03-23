---
title: Key Concepts
sidebar_label: Key Concepts
sidebar_position: 2
---

# Key Concepts

These are the core concepts you will encounter throughout DashAI.

## Dataset

A dataset is the collection of data you work with. It can be a table (CSV, Excel, JSON) or a set of images (ZIP). Every experiment in DashAI starts by loading a dataset.

Datasets are stored internally in Apache Arrow IPC format for efficient columnar access.

## Task

A task defines what type of ML problem you are solving. DashAI supports:

| Task | Description |
|------|-------------|
| Tabular Classification | Predict a category from structured table data |
| Regression | Predict a continuous numeric value |
| Text Classification | Assign categories to text documents |
| Translation | Translate text from one language to another |
| Text-to-Image Generation | Generate images from text prompts |
| Text-to-Text Generation | Generate or transform text (chat, summarization) |

## Experiment (Model Session)

An experiment associates a task with a dataset and a set of configuration choices: which columns are inputs, which column is the target, and how to split the data into train / validation / test subsets.

Internally, experiments are called **Model Sessions** in the API and database.

## Run

Each time you train a model inside an experiment, that is a **run**. If you train the same model with different parameters, those are separate runs. Runs can be compared side by side using their metrics.

## Metric

Metrics measure how well a model performs. DashAI automatically shows metrics relevant to your task:

| Task type | Available metrics |
|-----------|------------------|
| Classification | Accuracy, F1, Precision, Recall, ROC-AUC, Log Loss |
| Regression | RMSE, MAE, R², MSE, Explained Variance |
| Translation | BLEU, TER, ChrF |

## Explorer

An explorer is a visual analysis tool — box plots, correlation matrices, scatter plots, and more. Explorers operate on datasets and help you understand your data before modeling.

## Converter

A converter transforms data — normalizing values, encoding categories, removing columns, reducing dimensionality. Converters are applied as a preprocessing chain before a dataset is used for training.

## Job

Long-running operations (training, exploration, prediction) are executed as background **jobs**. The UI shows job status in real time so you can continue working while a model trains.
