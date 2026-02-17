from sklearn.svm import SVC as _SVC

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.scikit_learn.sklearn_like_model import (
    CategoricalEncodingStrategy,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class SVCSchema(BaseSchema):
    """Support Vector Machine (SVM) is a machine learning algorithm that separates data
    into different classes by finding the optimal hyperplane
    """

    C: schema_field(
        optimizer_float_field(gt=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 1.0,
            "upper_bound": 10.0,
        },
        description=MultilingualString(
            en=(
                "The parameter 'C' is a regularization parameter. "
                "The strength of the regularization is inversely proportional to C"
            ),
            es=(
                "El parámetro 'C' es un parámetro de regularización. "
                "La fuerza de la regularización es inversamente proporcional a C"
            ),
        ),
        alias=MultilingualString(en="C", es="C"),
    )  # type: ignore
    coef0: schema_field(
        optimizer_float_field(),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 1.0,
            "upper_bound": 10.0,
        },
        description=MultilingualString(
            en=(
                "The parameter 'coef0' is independent term in "
                "kernel function. "
                "It is only significant for kernel poly and sigmoid. "
            ),
            es=(
                "El parámetro 'coef0' es un término independiente en la "
                "función del kernel. "
                "Solo es significativo para los kernels poly y sigmoid. "
            ),
        ),
        alias=MultilingualString(en="coef0", es="coef0"),
    )  # type: ignore
    degree: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 1.0,
            "upper_bound": 10.0,
        },
        description=MultilingualString(
            en="The 'degree' parameter is only significant for 'poly' kernel.",
            es="El parámetro 'grado' solo es significativo para el kernel 'poly'.",
        ),
        alias=MultilingualString(en="degree", es="grado"),
    )  # type: ignore
    gamma: schema_field(
        enum_field(enum=["scale", "auto"]),
        placeholder="scale",
        description=MultilingualString(
            en="Coefficient for 'rbf', 'poly' and 'sigmoid' kernels.",
            es="Coeficiente para los kernels 'rbf', 'poly' y 'sigmoid'.",
        ),
        alias=MultilingualString(en="gamma", es="gamma"),
    )  # type: ignore
    kernel: schema_field(
        enum_field(enum=["linear", "poly", "rbf", "sigmoid"]),
        placeholder="rbf",
        description=MultilingualString(
            en="The 'kernel' parameter is the kernel used in the model.",
            es="El parámetro 'kernel' es el kernel utilizado en el modelo.",
        ),
        alias=MultilingualString(en="kernel", es="kernel"),
    )  # type: ignore
    max_iter: schema_field(
        optimizer_int_field(ge=-1),
        placeholder={
            "optimize": False,
            "fixed_value": -1,
            "lower_bound": -1,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "The 'max_iter' parameter determines the iteration limit for the "
                "solver. It must be of type positive integer "
                "or -1 to indicate no limit."
            ),
            es=(
                "El parámetro 'max_iter' determina el límite de iteraciones para el "
                "solucionador. Debe ser un entero positivo "
                "o -1 para indicar sin límite."
            ),
        ),
        alias=MultilingualString(en="max iterations", es="max iteraciones"),
    )  # type: ignore
    shrinking: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en=(
                "The 'shrinking' parameter determines whether "
                "a shrinking heuristic is used."
            ),
            es=(
                "El parámetro 'reducción' determina si "
                "se utiliza una heurística de reducción."
            ),
        ),
        alias=MultilingualString(en="shrinking", es="reducción"),
    )  # type: ignore
    tol: schema_field(
        optimizer_float_field(gt=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 1.0,
            "upper_bound": 10.0,
        },
        description=MultilingualString(
            en=("The parameter 'tol' determines the tolerance for the stop criterion."),
            es=(
                "El parámetro 'tol' determina "
                " la tolerancia para el criterio de detención."
            ),
        ),
        alias=MultilingualString(en="tolerance", es="tolerancia"),
    )  # type: ignore


class SVC(TabularClassificationModel, SklearnLikeClassifier, _SVC):
    """Scikit-learn's Support Vector Machine (SVM) classifier wrapper for DashAI."""

    SCHEMA = SVCSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Support Vector Machine (SVM)",
        es="Máquina de Vectores de Soporte (SVM)",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Support Vector Machine (SVM) is a supervised machine learning algorithm "
            "used for classification and regression tasks. It works by finding the "
            "optimal hyperplane that maximizes the margin between different classes "
            "in a high-dimensional feature space. SVMs are effective in cases where "
            "the number of features is large relative to the number of samples and "
            "can model complex, non-linear decision boundaries through the use of "
            "kernel functions such as linear, polynomial, and radial basis function "
            "(RBF) kernels."
        ),
        es=(
            "La Máquina de Vectores de Soporte (SVM) es un algoritmo de aprendizaje "
            "automático supervisado utilizado para tareas de clasificación y "
            "regresión. Funciona encontrando el hiperplano óptimo que maximiza el "
            "margen entre las distintas clases en un espacio de características de "
            "alta dimensionalidad. Las SVM son especialmente efectivas cuando el "
            "número de características es grande en relación con el número de "
            "muestras y pueden modelar fronteras de decisión complejas y no lineales "
            "mediante el uso de funciones kernel como lineal, polinomial y de base "
            "radial (RBF)."
        ),
    )
    COLOR: str = "#FF80AB"
    ICON: str = "Timeline"

    CATEGORICAL_ENCODING = CategoricalEncodingStrategy.ONE_HOT

    def __init__(self, **kwargs):
        kwargs["probability"] = True
        super().__init__(**kwargs)
