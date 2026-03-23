---
title: "Module Guide: Datasets"
sidebar_label: Datasets
sidebar_position: 1
---

# Module Guide: Datasets

The Datasets module is the entry point for all data in DashAI. From here you can load, inspect, explore, and transform your data before using it in experiments.

## Main Functions

- **Load data** — Upload CSV, Excel, JSON, or zipped image sets
- **Data summary** — Quick view of row count, column count, data types, and distributions
- **Exploration (EDA)** — Launch visual explorers directly from a dataset
- **Conversion** — Apply data converters (normalization, encoding, etc.)
- **Management** — Rename, delete, and inspect individual datasets

## Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV | `.csv` | Configurable delimiter |
| Excel | `.xlsx`, `.xls` | Select sheet, header row, and columns |
| JSON | `.json` | Specify the data key if nested |
| Images | `.zip` | ZIP of image folders, one folder per class |

## Available Dataloaders

Each file format has a dedicated dataloader with its own parameters:

- **CSVDataLoader** — delimiter, column names
- **JSONDataLoader** — data key path, column names
- **ExcelDataLoader** — sheet name, header row, columns to use
- **ImageDataLoader** — directory structure inside the ZIP

## Built-in Explorers

From the dataset view, you can launch any of these explorers:

| Explorer | What it shows |
|----------|--------------|
| BoxPlotExplorer | Value distribution per column |
| CorrelationMatrixExplorer | Correlation between variables |
| DescribeExplorer | Descriptive statistics |
| ScatterPlotExplorer | Relationship between pairs of variables |
| HistogramPlotExplorer | Frequency distributions |
| WordcloudExplorer | Word frequency for text columns |

## Built-in Converters

Converters transform your data to prepare it for modeling:

- **Scaling** — StandardScaler, MinMaxScaler, MaxAbsScaler, Normalizer
- **Encoding** — OneHotEncoder, OrdinalEncoder, LabelEncoder, LabelBinarizer
- **Imputation** — SimpleImputer, KNNImputer, MissingIndicator, NanRemover
- **Dimensionality Reduction** — PCA, TruncatedSVD, FastICA, IncrementalPCA
- **Feature Selection** — SelectKBest, SelectPercentile, VarianceThreshold
- **Resampling** — SMOTEConverter, RandomUnderSamplerConverter
- **Text** — TFIDFConverter, BagOfWordsConverter, TokenizerConverter, Embedding
