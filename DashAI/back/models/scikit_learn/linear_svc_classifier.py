from sklearn.svm import LinearSVC as _LinearSVC

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
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


class LinearSVCClassifierSchema(BaseSchema):
    """Schema that configures the Linear SVC Classifier.

    LinearSVC implements a linear Support Vector Classification trained with a
    linear kernel. It is faster than kernel SVC for large datasets. Because
    LinearSVC does not natively expose class probabilities, it is calibrated with
    Platt scaling (CalibratedClassifierCV). The underlying implementation is
    ``sklearn.svm.LinearSVC``.
    """

    C: schema_field(  # noqa: N815
        optimizer_float_field(ge=1e-4),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.01,
            "upper_bound": 100.0,
        },
        description=MultilingualString(
            en=(
                "Regularisation parameter. The strength of the regularisation is "
                "inversely proportional to C. Must be strictly positive."
            ),
            es=(
                "Parámetro de regularización. La fuerza de la regularización es "
                "inversamente proporcional a C. Debe ser estrictamente positivo."
            ),
        ),
        alias=MultilingualString(en="C", es="C"),
    )  # type: ignore

    loss: schema_field(
        enum_field(enum=["squared_hinge", "hinge"]),
        placeholder="squared_hinge",
        description=MultilingualString(
            en=(
                "Specifies the loss function. 'squared_hinge' is the default; "
                "'hinge' is the standard SVM loss."
            ),
            es=(
                "Especifica la función de pérdida. 'squared_hinge' es el "
                "predeterminado; 'hinge' es la pérdida estándar de SVM."
            ),
        ),
        alias=MultilingualString(en="Loss", es="Pérdida"),
    )  # type: ignore

    max_iter: schema_field(
        optimizer_int_field(ge=100),
        placeholder={
            "optimize": False,
            "fixed_value": 1000,
            "lower_bound": 100,
            "upper_bound": 10000,
        },
        description=MultilingualString(
            en="The maximum number of iterations to be run.",
            es="El número máximo de iteraciones a ejecutar.",
        ),
        alias=MultilingualString(en="Max iterations", es="Máximas iteraciones"),
    )  # type: ignore

    tol: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1e-4,
            "lower_bound": 1e-6,
            "upper_bound": 1e-1,
        },
        description=MultilingualString(
            en="Tolerance for stopping criteria.",
            es="Tolerancia para el criterio de parada.",
        ),
        alias=MultilingualString(en="Tolerance", es="Tolerancia"),
    )  # type: ignore

    fit_intercept: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en=(
                "Whether to calculate the intercept for this model. If False, "
                "the data is expected to be already centred."
            ),
            es=(
                "Si se calcula el intercepto para este modelo. Si es False, "
                "se espera que los datos ya estén centrados."
            ),
        ),
        alias=MultilingualString(en="Fit intercept", es="Ajustar intercepto"),
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


class LinearSVCClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _LinearSVC
):
    """Linear SVC classifier with Platt-scaling calibration for class probabilities.

    LinearSVC uses a linear kernel and is trained with coordinate descent, making
    it considerably faster than kernel SVC on large datasets. Because LinearSVC
    does not expose ``predict_proba`` natively, this wrapper fits a
    ``CalibratedClassifierCV`` with sigmoid calibration so that probability
    estimates are available to the DashAI evaluation pipeline.

    Key hyperparameters include ``C`` (regularisation), ``loss``, ``max_iter``,
    and ``fit_intercept``. The implementation wraps scikit-learn's ``LinearSVC``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html
    - [2] https://scikit-learn.org/stable/modules/calibration.html
    """

    SCHEMA = LinearSVCClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Linear SVC",
        es="SVC Lineal",
    )
    DESCRIPTION: str = MultilingualString(
        en="Fast linear support vector classifier with probability calibration.",
        es=(
            "Clasificador de vectores de soporte lineal rápido con "
            "calibración de probabilidades."
        ),
    )
    COLOR: str = "#FF7043"
    ICON: str = "LinearScale"
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
        """Train using CalibratedClassifierCV to expose predict_proba.

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
        from sklearn.svm import LinearSVC as _LinearSVCRaw

        x_processed = self.prepare_dataset(x_train, is_fit=True).to_pandas()
        y_processed = self.prepare_output(y_train, is_fit=True).to_pandas()
        y_arr = y_processed.values.ravel()

        params = {
            k: getattr(self, k)
            for k in ["C", "loss", "max_iter", "tol", "fit_intercept", "random_state"]
            if hasattr(self, k)
        }
        base = _LinearSVCRaw(**params)
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
