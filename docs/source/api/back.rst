================
DashAI Backend
================

This reference details all the backend components available in DashAI. For more information on how to add models, please refer to the :ref:`user_guide <user_guide>`.

.. currentmodule:: DashAI.back


Datasets
========

.. autosummary::
   :toctree: generated/

   DashAI.back.dataloaders.classes.dashai_dataset.DashAIDataset

Tasks
=====

.. autosummary::
   :toctree: generated/

   DashAI.back.tasks.BaseTask
   DashAI.back.tasks.RegressionTask
   DashAI.back.tasks.TabularClassificationTask
   DashAI.back.tasks.TextClassificationTask
   DashAI.back.tasks.TranslationTask

.. _models:

Models
======

.. autosummary::
   :toctree: generated/

   DashAI.back.models.BaseModel
   DashAI.back.models.SVC
   DashAI.back.models.BagOfWordsTextClassificationModel
   DashAI.back.models.DecisionTreeClassifier
   DashAI.back.models.DistilBertTransformer
   DashAI.back.models.DummyClassifier
   DashAI.back.models.GradientBoostingR
   DashAI.back.models.HistGradientBoostingClassifier
   DashAI.back.models.KNeighborsClassifier
   DashAI.back.models.LinearRegression
   DashAI.back.models.LinearSVR
   DashAI.back.models.LogisticRegression
   DashAI.back.models.MLPRegression
   DashAI.back.models.OpusMtEnESTransformer
   DashAI.back.models.RandomForestClassifier
   DashAI.back.models.RandomForestRegression
   DashAI.back.models.RidgeRegression

Dataloaders
===========

.. autosummary::
   :toctree: generated/

   DashAI.back.dataloaders.CSVDataLoader
   DashAI.back.dataloaders.ExcelDataLoader
   DashAI.back.dataloaders.JSONDataLoader

Metrics
=======

.. autosummary::
   :toctree: generated/

   DashAI.back.metrics.BaseMetric
   DashAI.back.metrics.F1
   DashAI.back.metrics.Accuracy
   DashAI.back.metrics.Precision
   DashAI.back.metrics.Recall
   DashAI.back.metrics.Bleu
   DashAI.back.metrics.MAE
   DashAI.back.metrics.RMSE
   DashAI.back.metrics.Ter

Optimizers
==========

.. autosummary::
   :toctree: generated/

   DashAI.back.optimizers.BaseOptimizer
   DashAI.back.optimizers.OptunaOptimizer
   DashAI.back.optimizers.HyperOptOptimizer

Jobs
====

.. autosummary::
   :toctree: generated/

   DashAI.back.job.ExplainerJob
   DashAI.back.job.DatasetJob
   DashAI.back.job.ModelJob
   DashAI.back.job.PredictJob
   DashAI.back.job.ExplorerJob
   DashAI.back.job.ConverterListJob

Explainers
==========

.. autosummary::
   :toctree: generated/

   DashAI.back.explainability.KernelShap
   DashAI.back.explainability.PartialDependence
   DashAI.back.explainability.PermutationFeatureImportance

Converters
==========

Base Converters
~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.base_converter.BaseConverter
   DashAI.back.converters.sklearn_wrapper.SklearnWrapper
   DashAI.back.converters.hugging_face_wrapper.HuggingFaceWrapper
   DashAI.back.converters.scikit_learn.sklearn_like_converter.SklearnLikeConverter

Feature Engineering
~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.ColumnRemover
   DashAI.back.converters.CharacterReplacer
   DashAI.back.converters.PolynomialFeatures
   DashAI.back.converters.Embedding

Scaling and Normalization
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.StandardScaler
   DashAI.back.converters.MinMaxScaler
   DashAI.back.converters.MaxAbsScaler
   DashAI.back.converters.Normalizer
   DashAI.back.converters.Binarizer

Encoding
~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.OneHotEncoder
   DashAI.back.converters.OrdinalEncoder
   DashAI.back.converters.LabelEncoder
   DashAI.back.converters.LabelBinarizer

Dimensionality Reduction
~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.PCA
   DashAI.back.converters.IncrementalPCA
   DashAI.back.converters.FastICA
   DashAI.back.converters.TruncatedSVD

Feature Selection
~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.VarianceThreshold
   DashAI.back.converters.GenericUnivariateSelect
   DashAI.back.converters.SelectKBest
   DashAI.back.converters.SelectPercentile
   DashAI.back.converters.SelectFpr
   DashAI.back.converters.SelectFdr
   DashAI.back.converters.SelectFwe

Imputation
~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.SimpleImputer
   DashAI.back.converters.KNNImputer
   DashAI.back.converters.MissingIndicator

Kernel Approximation
~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.AdditiveChi2Sampler
   DashAI.back.converters.RBFSampler
   DashAI.back.converters.SkewedChi2Sampler
   DashAI.back.converters.Nystroem

Sampling
~~~~~~~~

.. autosummary::
   :toctree: generated/

   DashAI.back.converters.SMOTEConverter
   DashAI.back.converters.SMOTEENNConverter
   DashAI.back.converters.RandomUnderSamplerConverter

Explorers
=========

.. autosummary::
   :toctree: generated/

   DashAI.back.exploration.BoxPlotExplorer
   DashAI.back.exploration.CorrelationMatrixExplorer
   DashAI.back.exploration.CovarianceMatrixExplorer
   DashAI.back.exploration.DensityHeatmapExplorer
   DashAI.back.exploration.DescribeExplorer
   DashAI.back.exploration.ECDFPlotExplorer
   DashAI.back.exploration.HistogramPlotExplorer
   DashAI.back.exploration.MultiColumnBoxPlotExplorer
   DashAI.back.exploration.ParallelCategoriesExplorer
   DashAI.back.exploration.ParallelCordinatesExplorer
   DashAI.back.exploration.RowExplorer
   DashAI.back.exploration.ScatterMatrixExplorer
   DashAI.back.exploration.ScatterPlotExplorer
   DashAI.back.exploration.WordcloudExplorer
