import logging

from DashAI.back.converters import (
    PCA,
    AdditiveChi2Sampler,
    Binarizer,
    CharacterReplacer,
    ColumnRemover,
    ConverterChain,
    Embedding,
    FastICA,
    GenericUnivariateSelect,
    IncrementalPCA,
    KNNImputer,
    LabelBinarizer,
    LabelEncoder,
    MaxAbsScaler,
    MinMaxScaler,
    MissingIndicator,
    Normalizer,
    Nystroem,
    OneHotEncoder,
    OrdinalEncoder,
    PolynomialFeatures,
    RandomUnderSamplerConverter,
    RBFSampler,
    SelectFdr,
    SelectFpr,
    SelectFwe,
    SelectKBest,
    SelectPercentile,
    SimpleImputer,
    SkewedChi2Sampler,
    SMOTEConverter,
    SMOTEENNConverter,
    StandardScaler,
    TruncatedSVD,
    VarianceThreshold,
)
from DashAI.back.dataloaders import CSVDataLoader, ExcelDataLoader, JSONDataLoader
from DashAI.back.explainability import (
    KernelShap,
    PartialDependence,
    PermutationFeatureImportance,
)
from DashAI.back.exploration import (
    BoxPlotExplorer,
    CorrelationMatrixExplorer,
    CovarianceMatrixExplorer,
    DensityHeatmapExplorer,
    DescribeExplorer,
    ECDFPlotExplorer,
    HistogramPlotExplorer,
    MultiColumnBoxPlotExplorer,
    ParallelCategoriesExplorer,
    ParallelCordinatesExplorer,
    RowExplorer,
    ScatterMatrixExplorer,
    ScatterPlotExplorer,
    WordcloudExplorer,
)
from DashAI.back.job import (
    ConverterListJob,
    DatasetJob,
    ExplainerJob,
    ExplorerJob,
    ModelJob,
    PredictJob,
)
from DashAI.back.metrics import F1, MAE, RMSE, Accuracy, Bleu, Precision, Recall, Ter
from DashAI.back.models import (
    SVC,
    BagOfWordsTextClassificationModel,
    DecisionTreeClassifier,
    DistilBertTransformer,
    DummyClassifier,
    GradientBoostingR,
    HistGradientBoostingClassifier,
    KNeighborsClassifier,
    LinearRegression,
    LinearSVR,
    LogisticRegression,
    MLPRegression,
    OpusMtEnESTransformer,
    RandomForestClassifier,
    RandomForestRegression,
    RidgeRegression,
)
from DashAI.back.optimizers import HyperOptOptimizer, OptunaOptimizer
from DashAI.back.plugins.utils import get_available_plugins
from DashAI.back.tasks import (
    ImageClassificationTask,
    RegressionTask,
    TabularClassificationTask,
    TextClassificationTask,
    TranslationTask,
)

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
        ImageClassificationTask,
        RegressionTask,
        # Models
        SVC,
        DecisionTreeClassifier,
        DummyClassifier,
        GradientBoostingR,
        HistGradientBoostingClassifier,
        KNeighborsClassifier,
        LogisticRegression,
        MLPRegression,
        RandomForestClassifier,
        RandomForestRegression,
        DistilBertTransformer,
        OpusMtEnESTransformer,
        BagOfWordsTextClassificationModel,
        RidgeRegression,
        LinearSVR,
        LinearRegression,
        # Dataloaders
        CSVDataLoader,
        JSONDataLoader,
        ExcelDataLoader,
        # Metrics
        F1,
        Accuracy,
        Precision,
        Recall,
        Bleu,
        Ter,
        MAE,
        RMSE,
        # Optimizers
        OptunaOptimizer,
        HyperOptOptimizer,
        # Jobs
        ExplainerJob,
        ModelJob,
        ExplorerJob,
        PredictJob,
        ConverterListJob,
        DatasetJob,
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
        CharacterReplacer,
        FastICA,
        IncrementalPCA,
        PCA,
        ConverterChain,
        TruncatedSVD,
        Binarizer,
        LabelBinarizer,
        LabelEncoder,
        MaxAbsScaler,
        MinMaxScaler,
        Normalizer,
        OneHotEncoder,
        OrdinalEncoder,
        PolynomialFeatures,
        StandardScaler,
        Embedding,
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
        CorrelationMatrixExplorer,
        CovarianceMatrixExplorer,
        DensityHeatmapExplorer,
        ECDFPlotExplorer,
        HistogramPlotExplorer,
        ScatterMatrixExplorer,
        ParallelCategoriesExplorer,
        ParallelCordinatesExplorer,
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
