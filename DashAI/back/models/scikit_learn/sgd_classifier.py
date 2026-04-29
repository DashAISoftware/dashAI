from sklearn.linear_model import SGDClassifier as _SGDClassifier

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
from DashAI.back.models.scikit_learn.sklearn_like_model import (
    CategoricalEncodingStrategy,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class SGDClassifierSchema(BaseSchema):
    """Schema that configures the SGD Classifier.

    SGDClassifier implements regularised linear classifiers (SVM, logistic
    regression, etc.) with Stochastic Gradient Descent training. The loss function
    determines the model type. Because not all loss functions expose
    ``predict_proba``, this wrapper always uses CalibratedClassifierCV for
    consistent probability estimates. The underlying implementation is
    ``sklearn.linear_model.SGDClassifier``.
    """

    loss: schema_field(
        enum_field(
            enum=[
                "hinge",
                "log_loss",
                "modified_huber",
                "squared_hinge",
                "perceptron",
            ]
        ),
        placeholder="hinge",
        description=MultilingualString(
            en=(
                "The loss function to use. 'hinge' gives a linear SVM; 'log_loss' "
                "gives logistic regression; 'modified_huber' is smoother; "
                "'squared_hinge' is like hinge but quadratically penalised; "
                "'perceptron' is the linear loss used by the perceptron algorithm."
            ),
            es=(
                "La función de pérdida a usar. 'hinge' da un SVM lineal; 'log_loss' "
                "da regresión logística; 'modified_huber' es más suave; "
                "'squared_hinge' es como hinge pero penalizado cuadráticamente; "
                "'perceptron' es la pérdida lineal usada por el algoritmo perceptrón."
            ),
        ),
        alias=MultilingualString(en="Loss", es="Pérdida"),
    )  # type: ignore

    alpha: schema_field(
        optimizer_float_field(ge=1e-6),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0001,
            "lower_bound": 1e-6,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "Regularisation parameter. Higher values result in stronger "
                "regularisation."
            ),
            es=(
                "Parámetro de regularización. Valores más altos resultan en "
                "regularización más fuerte."
            ),
        ),
        alias=MultilingualString(en="Alpha", es="Alfa"),
    )  # type: ignore

    max_iter: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1000,
            "lower_bound": 100,
            "upper_bound": 5000,
        },
        description=MultilingualString(
            en="The maximum number of passes over the training data (epochs).",
            es="El número máximo de pasadas sobre los datos de entrenamiento (épocas).",
        ),
        alias=MultilingualString(en="Max iterations", es="Máximas iteraciones"),
    )  # type: ignore

    tol: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1e-3,
            "lower_bound": 1e-6,
            "upper_bound": 1e-1,
        },
        description=MultilingualString(
            en=("The stopping criterion. Training stops when loss > best_loss - tol."),
            es=(
                "El criterio de parada. El entrenamiento se detiene cuando "
                "pérdida > mejor_pérdida - tol."
            ),
        ),
        alias=MultilingualString(en="Tolerance", es="Tolerancia"),
    )  # type: ignore

    learning_rate: schema_field(
        enum_field(enum=["constant", "optimal", "invscaling", "adaptive"]),
        placeholder="optimal",
        description=MultilingualString(
            en=(
                "The learning rate schedule. 'optimal' uses 1/(alpha*(t+t0)); "
                "'constant' keeps eta0 constant; 'invscaling' decreases as "
                "1/t^power; 'adaptive' halves the rate when training stops."
            ),
            es=(
                "El programa de tasa de aprendizaje. 'optimal' usa "
                "1/(alpha*(t+t0)); 'constant' mantiene eta0 constante; "
                "'invscaling' decrece como 1/t^power; 'adaptive' reduce a la "
                "mitad la tasa cuando el entrenamiento deja de mejorar."
            ),
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
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


class SGDClassifier(TabularClassificationModel, SklearnLikeClassifier, _SGDClassifier):
    """SGD classifier with probability calibration for consistent predict_proba output.

    SGDClassifier supports multiple loss functions that correspond to different
    linear models (SVM with 'hinge', logistic regression with 'log_loss', etc.).
    Stochastic Gradient Descent allows efficient training on large datasets. Because
    not all loss functions expose ``predict_proba`` natively, this wrapper
    consistently calibrates the model with ``CalibratedClassifierCV``.

    Key hyperparameters include ``loss``, ``alpha``, ``max_iter``, ``tol``, and
    ``learning_rate``. The implementation wraps scikit-learn's ``SGDClassifier``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDClassifier.html
    """

    SCHEMA = SGDClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="SGD Classifier",
        es="Clasificador SGD",
    )
    DESCRIPTION: str = MultilingualString(
        en="Linear classifier trained with stochastic gradient descent.",
        es="Clasificador lineal entrenado con descenso de gradiente estocástico.",
    )
    COLOR: str = "#78909C"
    ICON: str = "TrendingDown"
    CATEGORICAL_ENCODING = CategoricalEncodingStrategy.ONE_HOT

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
        self._calibrated = None

    def __sklearn_is_fitted__(self) -> bool:
        return self._calibrated is not None

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        """Train using CalibratedClassifierCV to guarantee predict_proba availability.

        Parameters
        ----------
        x_train : DashAIDataset
            The input features for training.
        y_train : DashAIDataset
            The target labels for training.
        x_validation : DashAIDataset, optional
            Unused (sklearn models ignore validation split).
        y_validation : DashAIDataset, optional
            Unused.

        Returns
        -------
        self
        """
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.linear_model import SGDClassifier as _SGDClassifierRaw

        x_processed = self.prepare_dataset(x_train, is_fit=True).to_pandas()
        y_processed = self.prepare_output(y_train, is_fit=True).to_pandas()
        y_arr = y_processed.values.ravel()

        params = {
            k: getattr(self, k)
            for k in [
                "loss",
                "alpha",
                "max_iter",
                "tol",
                "learning_rate",
                "random_state",
            ]
            if hasattr(self, k)
        }
        base = _SGDClassifierRaw(**params)
        self._calibrated = CalibratedClassifierCV(base, method="sigmoid", cv=3)
        self._calibrated.fit(x_processed, y_arr)
        return self

    def predict(self, x_pred) -> "ndarray":  # noqa: F821
        """Return class-probability matrix using the calibrated model.

        Parameters
        ----------
        x_pred : DashAIDataset or pd.DataFrame
            Input data.

        Returns
        -------
        np.ndarray
            Class probability matrix.
        """
        import pandas as pd

        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        if isinstance(x_pred, DashAIDataset):
            try:
                x_prepared = self.prepare_dataset(x_pred, is_fit=False)
            except ValueError:
                x_prepared = x_pred
            x_pred = x_prepared.to_pandas()
        elif isinstance(x_pred, pd.DataFrame):
            pass

        from sklearn.exceptions import NotFittedError

        if self._calibrated is None:
            raise NotFittedError(
                f"This {self.__class__.__name__} instance is not fitted yet. "
                "Call 'train' with appropriate arguments before using this estimator."
            )
        return self._calibrated.predict_proba(x_pred)
