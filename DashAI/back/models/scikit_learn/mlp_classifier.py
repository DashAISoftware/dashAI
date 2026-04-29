from sklearn.neural_network import MLPClassifier as _MLPClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class MLPClassifierSchema(BaseSchema):
    """Schema that configures the MLP Classifier.

    The Multi-layer Perceptron Classifier is a feedforward neural network trained
    with backpropagation. It supports multiple hidden layers and several activation
    functions. The underlying implementation is
    ``sklearn.neural_network.MLPClassifier``.
    """

    hidden_layer_size: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 10,
            "upper_bound": 500,
        },
        description=MultilingualString(
            en=(
                "Number of neurons in the single hidden layer. The model uses one "
                "hidden layer of this size."
            ),
            es=(
                "Número de neuronas en la capa oculta única. El modelo utiliza una "
                "capa oculta de este tamaño."
            ),
        ),
        alias=MultilingualString(en="Hidden layer size", es="Tamaño de capa oculta"),
    )  # type: ignore

    activation: schema_field(
        enum_field(enum=["relu", "tanh", "logistic", "identity"]),
        placeholder="relu",
        description=MultilingualString(
            en="Activation function for the hidden layer.",
            es="Función de activación para la capa oculta.",
        ),
        alias=MultilingualString(en="Activation", es="Activación"),
    )  # type: ignore

    solver: schema_field(
        enum_field(enum=["adam", "lbfgs", "sgd"]),
        placeholder="adam",
        description=MultilingualString(
            en=(
                "The solver for weight optimisation. 'adam' works well for large "
                "datasets; 'lbfgs' converges faster on small datasets; 'sgd' "
                "requires more tuning."
            ),
            es=(
                "El solucionador para la optimización de pesos. 'adam' funciona bien "
                "para datasets grandes; 'lbfgs' converge más rápido en datasets "
                "pequeños; 'sgd' requiere más ajuste."
            ),
        ),
        alias=MultilingualString(en="Solver", es="Solucionador"),
    )  # type: ignore

    alpha: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0001,
            "lower_bound": 1e-6,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en="L2 regularisation term (penalty parameter).",
            es="Término de regularización L2 (parámetro de penalización).",
        ),
        alias=MultilingualString(en="Alpha", es="Alfa"),
    )  # type: ignore

    learning_rate_init: schema_field(
        optimizer_float_field(ge=1e-6),
        placeholder={
            "optimize": False,
            "fixed_value": 0.001,
            "lower_bound": 1e-5,
            "upper_bound": 0.1,
        },
        description=MultilingualString(
            en="The initial learning rate used for weight updates.",
            es="La tasa de aprendizaje inicial usada para actualizar los pesos.",
        ),
        alias=MultilingualString(
            en="Learning rate init", es="Tasa de aprendizaje inicial"
        ),
    )  # type: ignore

    max_iter: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 200,
            "lower_bound": 50,
            "upper_bound": 1000,
        },
        description=MultilingualString(
            en=(
                "Maximum number of iterations. The solver iterates until "
                "convergence or this limit."
            ),
            es=(
                "Número máximo de iteraciones. El solucionador itera hasta "
                "convergencia o este límite."
            ),
        ),
        alias=MultilingualString(en="Max iterations", es="Máximas iteraciones"),
    )  # type: ignore

    random_state: schema_field(
        union_type(optimizer_int_field(ge=0), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The seed of the pseudo-random number generator. Pass an int for "
                "reproducible output, or None to not set a specific seed."
            ),
            es=(
                "La semilla del generador de números pseudoaleatorios. Pase un int "
                "para salida reproducible, o None para no fijar una semilla."
            ),
        ),
        alias=MultilingualString(en="Random state", es="Estado aleatorio"),
    )  # type: ignore


class MLPClassifier(TabularClassificationModel, SklearnLikeClassifier, _MLPClassifier):
    """Multi-layer Perceptron classifier trained with backpropagation.

    MLPClassifier is a fully-connected feedforward neural network. The network
    uses a single hidden layer whose size is controlled by ``hidden_layer_size``.
    Training uses backpropagation with the selected ``solver``. Supports ReLU,
    tanh, logistic, and identity activations.

    Key hyperparameters include ``hidden_layer_size``, ``activation``, ``solver``,
    ``alpha`` (L2 regularisation), ``learning_rate_init``, and ``max_iter``. The
    implementation wraps scikit-learn's ``MLPClassifier``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html
    """

    SCHEMA = MLPClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="MLP Classifier",
        es="Clasificador MLP",
    )
    DESCRIPTION: str = MultilingualString(
        en="Multi-layer perceptron neural network for tabular classification.",
        es="Red neuronal perceptrón multicapa para clasificación tabular.",
    )
    COLOR: str = "#EF5350"
    ICON: str = "AccountTree"

    def __init__(self, **kwargs) -> None:
        """Initialise the model, converting hidden_layer_size to a tuple for sklearn.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values; ``hidden_layer_size`` is converted to a tuple
            ``(hidden_layer_size,)`` before being forwarded to sklearn's MLPClassifier.
        """
        hidden_size = kwargs.pop("hidden_layer_size", 100)
        kwargs["hidden_layer_sizes"] = (hidden_size,)
        super().__init__(**kwargs)
