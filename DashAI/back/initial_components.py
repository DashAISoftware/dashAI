import logging

# Hugging Face module
from DashAI.back.converters.hugging_face.embedding import Embedding
from DashAI.back.converters.hugging_face.tokenizer import TokenizerConverter

# Imbalanced_learn
from DashAI.back.converters.imbalanced_learn.random_under_sampler_converter import (
    RandomUnderSamplerConverter,
)
from DashAI.back.converters.imbalanced_learn.smote_converter import SMOTEConverter
from DashAI.back.converters.imbalanced_learn.smoteenn_converter import SMOTEENNConverter

# Kernel approximation module
from DashAI.back.converters.scikit_learn.additive_chi_2_sampler import (
    AdditiveChi2Sampler,
)
from DashAI.back.converters.scikit_learn.bag_of_words import BagOfWordsConverter

# Preprocessing module
from DashAI.back.converters.scikit_learn.binarizer import Binarizer

# Decomposition module
from DashAI.back.converters.scikit_learn.fast_ica import FastICA

# Feature selection module
from DashAI.back.converters.scikit_learn.generic_univariate_select import (
    GenericUnivariateSelect,
)
from DashAI.back.converters.scikit_learn.incremental_pca import IncrementalPCA
from DashAI.back.converters.scikit_learn.knn_imputer import KNNImputer
from DashAI.back.converters.scikit_learn.label_encoder import LabelEncoder
from DashAI.back.converters.scikit_learn.max_abs_scaler import MaxAbsScaler
from DashAI.back.converters.scikit_learn.min_max_scaler import MinMaxScaler
from DashAI.back.converters.scikit_learn.missing_indicator import MissingIndicator
from DashAI.back.converters.scikit_learn.normalizer import Normalizer
from DashAI.back.converters.scikit_learn.nystroem import Nystroem
from DashAI.back.converters.scikit_learn.one_hot_encoder import OneHotEncoder
from DashAI.back.converters.scikit_learn.ordinal_encoder import OrdinalEncoder
from DashAI.back.converters.scikit_learn.pca import PCA
from DashAI.back.converters.scikit_learn.polynomial_features import PolynomialFeatures
from DashAI.back.converters.scikit_learn.rbf_sampler import RBFSampler
from DashAI.back.converters.scikit_learn.select_fdr import SelectFdr
from DashAI.back.converters.scikit_learn.select_fpr import SelectFpr
from DashAI.back.converters.scikit_learn.select_fwe import SelectFwe
from DashAI.back.converters.scikit_learn.select_k_best import SelectKBest
from DashAI.back.converters.scikit_learn.select_percentile import SelectPercentile

# Impute module
from DashAI.back.converters.scikit_learn.simple_imputer import SimpleImputer
from DashAI.back.converters.scikit_learn.skewed_chi_2_sampler import SkewedChi2Sampler
from DashAI.back.converters.scikit_learn.standard_scaler import StandardScaler
from DashAI.back.converters.scikit_learn.tf_idf import TFIDFConverter
from DashAI.back.converters.scikit_learn.truncated_svd import TruncatedSVD
from DashAI.back.converters.scikit_learn.variance_threshold import VarianceThreshold

# Simple converters
from DashAI.back.converters.simple_converters.character_replacer import (
    CharacterReplacer,
)
from DashAI.back.converters.simple_converters.column_remover import ColumnRemover
from DashAI.back.converters.simple_converters.nan_remover import NanRemover

# DataLoaders
from DashAI.back.dataloaders.classes.arrow_dataloader import ArrowDataLoader
from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader
from DashAI.back.dataloaders.classes.excel_dataloader import ExcelDataLoader
from DashAI.back.dataloaders.classes.json_dataloader import JSONDataLoader

# Explainers
from DashAI.back.explainability.explainers.kernel_shap import KernelShap
from DashAI.back.explainability.explainers.partial_dependence import PartialDependence
from DashAI.back.explainability.explainers.permutation_feature_importance import (
    PermutationFeatureImportance,
)

# Explorers
from DashAI.back.exploration.explorers.box_plot import BoxPlotExplorer
from DashAI.back.exploration.explorers.corr_matrix import CorrelationMatrixExplorer
from DashAI.back.exploration.explorers.cov_matrix import CovarianceMatrixExplorer
from DashAI.back.exploration.explorers.density_heatmap import DensityHeatmapExplorer
from DashAI.back.exploration.explorers.describe_explorer import DescribeExplorer
from DashAI.back.exploration.explorers.ecdf_plot import ECDFPlotExplorer
from DashAI.back.exploration.explorers.histogram_plot import HistogramPlotExplorer
from DashAI.back.exploration.explorers.multibox_plot import MultiColumnBoxPlotExplorer
from DashAI.back.exploration.explorers.parallel_categories import (
    ParallelCategoriesExplorer,
)
from DashAI.back.exploration.explorers.parallel_cordinates import (
    ParallelCordinatesExplorer,
)
from DashAI.back.exploration.explorers.row_explorer import RowExplorer
from DashAI.back.exploration.explorers.scatter_matrix import ScatterMatrixExplorer
from DashAI.back.exploration.explorers.scatter_plot import ScatterPlotExplorer
from DashAI.back.exploration.explorers.wordcloud import WordcloudExplorer

# Jobs
from DashAI.back.job.converter_job import ConverterJob
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.explainer_job import ExplainerJob
from DashAI.back.job.explorer_job import ExplorerJob
from DashAI.back.job.generative_job import GenerativeJob
from DashAI.back.job.model_job import ModelJob
from DashAI.back.job.pipeline_job import PipelineJob
from DashAI.back.job.predict_job import PredictJob

# Metrics
from DashAI.back.metrics.classification.accuracy import Accuracy
from DashAI.back.metrics.classification.cohen_kappa import CohenKappa
from DashAI.back.metrics.classification.f1 import F1
from DashAI.back.metrics.classification.hamming_distance import HammingDistance
from DashAI.back.metrics.classification.log_loss import LogLoss
from DashAI.back.metrics.classification.precision import Precision
from DashAI.back.metrics.classification.recall import Recall
from DashAI.back.metrics.classification.roc_auc import ROCAUC
from DashAI.back.metrics.regression.explained_variance import ExplainedVariance
from DashAI.back.metrics.regression.mae import MAE
from DashAI.back.metrics.regression.median_absolute_error import MedianAbsoluteError
from DashAI.back.metrics.regression.mse import MSE
from DashAI.back.metrics.regression.r2 import R2
from DashAI.back.metrics.regression.rmse import RMSE
from DashAI.back.metrics.translation.bleu import Bleu
from DashAI.back.metrics.translation.chrf import Chrf
from DashAI.back.metrics.translation.ter import Ter

# Models
from DashAI.back.models.hugging_face.albert_transformer import AlbertTransformer
from DashAI.back.models.hugging_face.bert_transformer import BertTransformer
from DashAI.back.models.hugging_face.bertin_transformer import BertinTransformer
from DashAI.back.models.hugging_face.beto_transformer import BetoTransformer
from DashAI.back.models.hugging_face.deberta_v3_transformer import DebertaV3Transformer
from DashAI.back.models.hugging_face.distilbert_transformer import DistilBertTransformer
from DashAI.back.models.hugging_face.electra_transformer import ElectraTransformer
from DashAI.back.models.hugging_face.llama_model import LlamaModel
from DashAI.back.models.hugging_face.m2m100_transformer import M2M100Transformer
from DashAI.back.models.hugging_face.minilm_transformer import MiniLMTransformer
from DashAI.back.models.hugging_face.mistral_model import MistralModel
from DashAI.back.models.hugging_face.mixtral_model import MixtralModel
from DashAI.back.models.hugging_face.modernbert_transformer import ModernBertTransformer
from DashAI.back.models.hugging_face.multilingual_bert_transformer import (
    MultilingualBertTransformer,
)
from DashAI.back.models.hugging_face.nllb_transformer import NllbTransformer
from DashAI.back.models.hugging_face.opus_mt_en_de_transformer import (
    OpusMtEnDeTransformer,
)
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformer,
)
from DashAI.back.models.hugging_face.opus_mt_en_fr_transformer import (
    OpusMtEnFrTransformer,
)
from DashAI.back.models.hugging_face.opus_mt_en_pt_transformer import (
    OpusMtEnPtTransformer,
)
from DashAI.back.models.hugging_face.opus_mt_es_en_transformer import (
    OpusMtEsENTransformer,
)
from DashAI.back.models.hugging_face.opus_mt_fr_en_transformer import (
    OpusMtFrEnTransformer,
)
from DashAI.back.models.hugging_face.pixart_sigma_model import PixArtSigmaModel
from DashAI.back.models.hugging_face.qwen_model import QwenModel
from DashAI.back.models.hugging_face.roberta_transformer import RobertaTransformer
from DashAI.back.models.hugging_face.sd15_depth_controlnet_model import (
    SD15DepthControlNetModel,
)
from DashAI.back.models.hugging_face.sd15_hed_controlnet_model import (
    SD15HEDControlNetModel,
)
from DashAI.back.models.hugging_face.sd15_openpose_controlnet_model import (
    SD15OpenPoseControlNetModel,
)
from DashAI.back.models.hugging_face.sdxl_canny_controlnet_model import (
    SDXLCannyControlNetModel,
)
from DashAI.back.models.hugging_face.sdxl_turbo_model import SDXLTurboModel
from DashAI.back.models.hugging_face.smol_lm_model import SmolLMModel
from DashAI.back.models.hugging_face.stable_diffusion_v1_depth_controlnet import (
    StableDiffusionXLV1ControlNet,
)
from DashAI.back.models.hugging_face.stable_diffusion_v2_model import (
    StableDiffusionV2Model,
)
from DashAI.back.models.hugging_face.stable_diffusion_v3_model import (
    StableDiffusionV3Model,
)
from DashAI.back.models.hugging_face.stable_diffusion_xl_model import (
    StableDiffusionXLModel,
)
from DashAI.back.models.hugging_face.t5_small_transformer import T5SmallTransformer
from DashAI.back.models.hugging_face.tongyi_z_image_model import TongyiZImageModel
from DashAI.back.models.hugging_face.xlm_roberta_transformer import (
    XlmRobertaTransformer,
)
from DashAI.back.models.hugging_face.xlnet_transformer import XlnetTransformer
from DashAI.back.models.scikit_learn.adaboost_classifier import AdaBoostClassifier
from DashAI.back.models.scikit_learn.adaboost_regression import AdaBoostRegression
from DashAI.back.models.scikit_learn.bagging_classifier import BaggingClassifier
from DashAI.back.models.scikit_learn.bayesian_ridge_regression import (
    BayesianRidgeRegression,
)
from DashAI.back.models.scikit_learn.bow_text_classification_model import (
    BagOfWordsTextClassificationModel,
)
from DashAI.back.models.scikit_learn.decision_tree_classifier import (
    DecisionTreeClassifier,
)
from DashAI.back.models.scikit_learn.decision_tree_regression import (
    DecisionTreeRegression,
)
from DashAI.back.models.scikit_learn.dummy_classifier import DummyClassifier
from DashAI.back.models.scikit_learn.elastic_net_regression import ElasticNetRegression
from DashAI.back.models.scikit_learn.extra_trees_classifier import ExtraTreesClassifier
from DashAI.back.models.scikit_learn.extra_trees_regression import ExtraTreesRegression
from DashAI.back.models.scikit_learn.gaussian_nb import GaussianNB
from DashAI.back.models.scikit_learn.gradient_boosting_classifier import (
    GradientBoostingClassifier,
)
from DashAI.back.models.scikit_learn.gradient_boosting_regression import (
    GradientBoostingR,
)
from DashAI.back.models.scikit_learn.hist_gradient_boosting_classifier import (
    HistGradientBoostingClassifier,
)
from DashAI.back.models.scikit_learn.hist_gradient_boosting_regression import (
    HistGradientBoostingRegression,
)
from DashAI.back.models.scikit_learn.k_neighbors_classifier import KNeighborsClassifier
from DashAI.back.models.scikit_learn.k_neighbors_regression import KNeighborsRegression
from DashAI.back.models.scikit_learn.lasso_regression import LassoRegression
from DashAI.back.models.scikit_learn.linear_regression import LinearRegression
from DashAI.back.models.scikit_learn.linear_svc_classifier import LinearSVCClassifier
from DashAI.back.models.scikit_learn.linearSVR import LinearSVR
from DashAI.back.models.scikit_learn.logistic_regression import LogisticRegression
from DashAI.back.models.scikit_learn.mlp_classifier import MLPClassifier
from DashAI.back.models.scikit_learn.mlp_regression import MLPRegression
from DashAI.back.models.scikit_learn.random_forest_classifier import (
    RandomForestClassifier,
)
from DashAI.back.models.scikit_learn.random_forest_regression import (
    RandomForestRegression,
)
from DashAI.back.models.scikit_learn.ridge_regression import RidgeRegression
from DashAI.back.models.scikit_learn.sgd_classifier import SGDClassifier
from DashAI.back.models.scikit_learn.svc import SVC
from DashAI.back.models.scikit_learn.svr import SVR
from DashAI.back.models.scikit_learn.tfidf_logreg_text_classification_model import (
    TfIdfLogRegTextClassificationModel,
)

# Optimizers
from DashAI.back.optimizers.hyperopt_optimizer import HyperOptOptimizer
from DashAI.back.optimizers.optuna_optimizer import OptunaOptimizer

# Pipeline nodes
from DashAI.back.pipeline.data_selector_node import DataSelector
from DashAI.back.pipeline.exploration_node import DataExploration
from DashAI.back.pipeline.prediction_node import Prediction
from DashAI.back.pipeline.retrieve_model_node import RetrieveModel
from DashAI.back.pipeline.train_node import Train

# Plugins
from DashAI.back.plugins.utils import get_available_plugins

# Tasks
from DashAI.back.tasks.controlnet_task import ControlNetTask
from DashAI.back.tasks.regression_task import RegressionTask
from DashAI.back.tasks.tabular_classification_task import TabularClassificationTask
from DashAI.back.tasks.text_classification_task import TextClassificationTask
from DashAI.back.tasks.text_to_image_generation_task import TextToImageGenerationTask
from DashAI.back.tasks.text_to_text_generation_task import TextToTextGenerationTask
from DashAI.back.tasks.translation_task import TranslationTask

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def get_initial_components():
    """
    Obtiene todos los componentes iniciales, incluyendo los básicos
    y los plugins instalados.

    Returns
    -------
    List[type]
        Lista de todas las clases de componentes disponibles
    """
    # Componentes básicos que siempre deben estar disponibles
    basic_components = [
        # Tasks
        TabularClassificationTask,
        TextClassificationTask,
        TranslationTask,
        RegressionTask,
        TextToImageGenerationTask,
        TextToTextGenerationTask,
        ControlNetTask,
        # Models
        AdaBoostClassifier,
        AlbertTransformer,
        AdaBoostRegression,
        BaggingClassifier,
        BagOfWordsTextClassificationModel,
        BertTransformer,
        BertinTransformer,
        BetoTransformer,
        BayesianRidgeRegression,
        DebertaV3Transformer,
        DecisionTreeClassifier,
        DecisionTreeRegression,
        DistilBertTransformer,
        DummyClassifier,
        ElasticNetRegression,
        ElectraTransformer,
        ExtraTreesClassifier,
        ExtraTreesRegression,
        GaussianNB,
        GradientBoostingClassifier,
        GradientBoostingR,
        HistGradientBoostingClassifier,
        HistGradientBoostingRegression,
        KNeighborsClassifier,
        KNeighborsRegression,
        LassoRegression,
        LinearRegression,
        LinearSVCClassifier,
        LinearSVR,
        LlamaModel,
        LogisticRegression,
        M2M100Transformer,
        MiniLMTransformer,
        MistralModel,
        MixtralModel,
        MultilingualBertTransformer,
        MLPClassifier,
        MLPRegression,
        ModernBertTransformer,
        NllbTransformer,
        OpusMtEnDeTransformer,
        OpusMtEnESTransformer,
        OpusMtEnFrTransformer,
        OpusMtEnPtTransformer,
        OpusMtEsENTransformer,
        OpusMtFrEnTransformer,
        PixArtSigmaModel,
        QwenModel,
        RandomForestClassifier,
        RobertaTransformer,
        RandomForestRegression,
        RidgeRegression,
        SD15DepthControlNetModel,
        SD15HEDControlNetModel,
        SD15OpenPoseControlNetModel,
        SDXLCannyControlNetModel,
        SDXLTurboModel,
        SGDClassifier,
        SmolLMModel,
        StableDiffusionV2Model,
        StableDiffusionV3Model,
        StableDiffusionXLModel,
        StableDiffusionXLV1ControlNet,
        SVC,
        SVR,
        T5SmallTransformer,
        TfIdfLogRegTextClassificationModel,
        TongyiZImageModel,
        XlmRobertaTransformer,
        XlnetTransformer,
        # Dataloaders
        ArrowDataLoader,
        CSVDataLoader,
        ExcelDataLoader,
        JSONDataLoader,
        # Metrics
        F1,
        Accuracy,
        Precision,
        Recall,
        Bleu,
        Ter,
        Chrf,
        MSE,
        RMSE,
        MAE,
        R2,
        MedianAbsoluteError,
        ExplainedVariance,
        ROCAUC,
        LogLoss,
        HammingDistance,
        CohenKappa,
        # Optimizers
        OptunaOptimizer,
        HyperOptOptimizer,
        # Jobs
        ExplainerJob,
        ModelJob,
        ExplorerJob,
        PredictJob,
        ConverterJob,
        DatasetJob,
        GenerativeJob,
        PipelineJob,
        # Explainers
        KernelShap,
        PartialDependence,
        PermutationFeatureImportance,
        # Explorers
        DescribeExplorer,
        ScatterPlotExplorer,
        WordcloudExplorer,
        RowExplorer,
        BoxPlotExplorer,
        MultiColumnBoxPlotExplorer,
        CorrelationMatrixExplorer,
        CovarianceMatrixExplorer,
        DensityHeatmapExplorer,
        ECDFPlotExplorer,
        HistogramPlotExplorer,
        ScatterMatrixExplorer,
        ParallelCategoriesExplorer,
        ParallelCordinatesExplorer,
        # Converters
        ColumnRemover,
        NanRemover,
        CharacterReplacer,
        FastICA,
        IncrementalPCA,
        PCA,
        TruncatedSVD,
        Binarizer,
        LabelEncoder,
        MaxAbsScaler,
        MinMaxScaler,
        Normalizer,
        OneHotEncoder,
        OrdinalEncoder,
        PolynomialFeatures,
        StandardScaler,
        Embedding,
        TFIDFConverter,
        TokenizerConverter,
        BagOfWordsConverter,
        VarianceThreshold,
        SimpleImputer,
        MissingIndicator,
        KNNImputer,
        AdditiveChi2Sampler,
        RBFSampler,
        SkewedChi2Sampler,
        GenericUnivariateSelect,
        SelectPercentile,
        SelectKBest,
        SelectFpr,
        SelectFdr,
        SelectFwe,
        Nystroem,
        DataSelector,
        DataExploration,
        Train,
        RetrieveModel,
        Prediction,
        SMOTEConverter,
        SMOTEENNConverter,
        RandomUnderSamplerConverter,
    ]

    # Obtener plugins instalados
    try:
        installed_plugins = get_available_plugins()
        log.info(f"Se cargaron {len(installed_plugins)} plugins instalados")
    except Exception as e:
        log.error(f"Error al cargar plugins instalados: {str(e)}")
        installed_plugins = []

    return basic_components + installed_plugins
