---
title: "Flow: Text Classification"
sidebar_label: Text Classification
sidebar_position: 3
---

# Flow: Text Classification

This flow covers end-to-end text classification — from loading a text corpus to classifying new documents with a transformer model.

## Objective

Train a text classifier on a labeled corpus (e.g., product reviews with sentiment labels) using DistilBERT.

## 1. Load the Text Corpus

Load a CSV dataset where one column contains the text and another contains the category label. Example: product reviews with positive/negative/neutral sentiment labels.

## 2. Explore the Text

Use **WordcloudExplorer** to visualize the most frequent words per category. Use **DescribeExplorer** to check the class distribution — are categories balanced?

:::tip
Imbalanced classes are very common in text datasets. If one class dominates, F1-Score is a more informative metric than Accuracy.
:::

## 3. Configure the Experiment

Create an experiment with task **Text Classification**. Select the text column as input and the label column as target. Add **DistilBertTransformer** as the model.

## 4. Train and Evaluate

Train the model. Review classification metrics: Accuracy, F1-Score, Precision, and Recall. For text classification, per-class F1 is particularly informative when classes are imbalanced.

:::note
Transformer models like DistilBERT require significantly more training time than tabular models, but deliver substantially better results on text data.
:::
