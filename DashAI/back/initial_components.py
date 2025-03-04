import logging

from DashAI.back.dataloaders import CSVDataLoader, ImageDataLoader, JSONDataLoader
from DashAI.back.explainability import (
    KernelShap,
    PartialDependence,
    PermutationFeatureImportance,
)
from DashAI.back.job import ExplainerJob, ModelJob
from DashAI.back.metrics import F1, Accuracy, Bleu, Precision, Recall
from DashAI.back.models import (
    SVC,
    BagOfWordsTextClassificationModel,
    DecisionTreeClassifier,
    DistilBertTransformer,
    DummyClassifier,
    HistGradientBoostingClassifier,
    KNeighborsClassifier,
    LogisticRegression,
    OpusMtEnESTransformer,
    RandomForestClassifier,
    ViTTransformer,
)
from DashAI.back.plugins.utils import get_available_plugins
from DashAI.back.tasks import (
    ImageClassificationTask,
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
        # Models
        SVC,
        DecisionTreeClassifier,
        DummyClassifier,
        HistGradientBoostingClassifier,
        KNeighborsClassifier,
        LogisticRegression,
        RandomForestClassifier,
        DistilBertTransformer,
        ViTTransformer,
        OpusMtEnESTransformer,
        BagOfWordsTextClassificationModel,
        # Dataloaders
        CSVDataLoader,
        JSONDataLoader,
        ImageDataLoader,
        # Metrics
        F1,
        Accuracy,
        Precision,
        Recall,
        Bleu,
        # Jobs
        ExplainerJob,
        ModelJob,
        # Explainers
        KernelShap,
        PartialDependence,
        PermutationFeatureImportance,
    ]

    # Obtener plugins instalados
    try:
        installed_plugins = get_available_plugins()
        log.info(f"Se cargaron {len(installed_plugins)} plugins instalados")
    except Exception as e:
        log.error(f"Error al cargar plugins instalados: {str(e)}")
        installed_plugins = []

    return basic_components + installed_plugins
