import logging

from DashAI.back.converters import (
    PCA,
    AdditiveChi2Sampler,
    BagOfWordsConverter,
    Binarizer,
    CharacterReplacer,
    ColumnRemover,
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
    NanRemover,
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
    TFIDFConverter,
    TokenizerConverter,
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
    GenerativeJob,
    ModelJob,
    PipelineJob,
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
    QwenModel,
    RandomForestClassifier,
    RandomForestRegression,
    RidgeRegression,
    StableDiffusionV2Model,
    StableDiffusionV3Model,
    StableDiffusionXLV1ControlNet,
    OpenAITextToTextGenerationModel,
    Phi4MiniInstructModel,
)
from DashAI.back.models.RAG import (
    RAGPipeline,
    # Prompts
    DefaultGenerationPrompt,
    CustomGenerationPrompt,
    DefaultQnAGenerationPrompt,
    #DefaultAugmentationPrompt,
    CustomAugmentationPrompt,
    # Chunking Models
    CharacterChunkModel,
    TokenChunkModel,
    # Retrievers
    DenseRetriever,
    # Encodings
    # DenseEmbedding,
    FastTextEmbedding,
    HuggingFaceEmbedding,
    # Pipeline
    RAGPipeline,
    SparseRetriever,
    TFIDFRetriever,
    TFIDFVectorizerModel,
    TokenChunkModel,
    
)
from DashAI.back.optimizers import HyperOptOptimizer, OptunaOptimizer
from DashAI.back.pipeline import (
    DataExploration,
    DataSelector,
    Prediction,
    RetrieveModel,
    Train,
)
from DashAI.back.plugins.utils import get_available_plugins
from DashAI.back.tasks import (
    ControlNetTask,
    ImageClassificationTask,
    RAGTask,
    RegressionTask,
    TabularClassificationTask,
    TextClassificationTask,
    TextToImageGenerationTask,
    TextToTextGenerationTask,
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
        TextToImageGenerationTask,
        TextToTextGenerationTask,
        ControlNetTask,
        RAGTask,
        # Models
        SVC,
        DecisionTreeClassifier,
        DummyClassifier,
        GradientBoostingR,
        HistGradientBoostingClassifier,
        KNeighborsClassifier,
        QwenModel,
        RAGPipeline,
        StableDiffusionV2Model,
        StableDiffusionV3Model,
        StableDiffusionXLV1ControlNet,
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
        OpenAITextToTextGenerationModel,
        Phi4MiniInstructModel,
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
        CorrelationMatrixExplorer,
        CovarianceMatrixExplorer,
        DensityHeatmapExplorer,
        ECDFPlotExplorer,
        HistogramPlotExplorer,
        ScatterMatrixExplorer,
        ParallelCategoriesExplorer,
        ParallelCordinatesExplorer,
        DataSelector,
        DataExploration,
        Train,
        RetrieveModel,
        Prediction,
        SMOTEConverter,
        SMOTEENNConverter,
        RandomUnderSamplerConverter,
        # RAG
        RAGPipeline,
        # Chunking Models
        CharacterChunkModel,
        TokenChunkModel,
        # Encodings
        FastTextEmbedding,
        HuggingFaceEmbedding,
        # Prompts
        DefaultGenerationPrompt,
        CustomGenerationPrompt,
        DefaultQnAGenerationPrompt,
        #DefaultAugmentationPrompt,
        CustomAugmentationPrompt,
        # Retrievers
        DenseRetriever,
        SparseRetriever,
        TFIDFRetriever,
        TFIDFVectorizerModel,
    ]

    # Obtener plugins instalados
    try:
        installed_plugins = get_available_plugins()
        log.info(f"Se cargaron {len(installed_plugins)} plugins instalados")
    except Exception as e:
        log.error(f"Error al cargar plugins instalados: {str(e)}")
        installed_plugins = []

    return basic_components + installed_plugins
