from tabpfn import TabPFNClassifier as _TabPFNClassifier

from DashAI.back.core.schema_fields import BaseSchema, optimizer_int_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class TabPFNClassifierSchema(BaseSchema):
    """Schema that configures the TabPFN Classifier.

    TabPFN is a pretrained transformer model for tabular classification that
    leverages prior-data fitted networks. It handles preprocessing internally
    and achieves strong performance with minimal configuration.
    The underlying implementation is ``tabpfn.TabPFNClassifier``.
    """

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 4,
            "lower_bound": 1,
            "upper_bound": 16,
        },
        description=MultilingualString(
            en=(
                "The 'n_estimators' parameter controls the number of ensemble "
                "configurations used during inference. Higher values improve accuracy "
                "at the cost of speed. It must be an integer greater than or "
                "equal to 1."
            ),
            es=(
                "El parámetro 'n_estimators' controla el número de configuraciones "
                "de conjunto utilizadas durante la inferencia. Valores más altos "
                "mejoran la "
                "precisión a costa de velocidad. Debe ser un entero mayor o igual a 1."
            ),
        ),
        alias=MultilingualString(en="N estimators", es="N estimadores"),
    )  # type: ignore


class TabPFNClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _TabPFNClassifier
):
    """TabPFN classifier based on prior-data fitted networks.

    TabPFN is a pretrained transformer model that performs in-context learning
    for tabular classification. It encodes the training set as context and
    performs a single forward pass to predict test labels — no gradient updates
    occur at fit time. The model handles its own feature preprocessing internally,
    so no manual scaling or one-hot encoding should be applied beforehand.

    Key hyperparameters include ``n_estimators`` (number of ensemble
    configurations). GPU is strongly recommended for datasets larger than
    ~1 000 samples.

    References
    ----------
    - [1] Hollmann, N., et al. (2025). "TabPFN v2: Improved Solution for
           Tabular Classification and Regression."
           https://arxiv.org/abs/2501.02945
    - [2] https://github.com/PriorLabs/TabPFN
    """

    SCHEMA = TabPFNClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="TabPFN",
        es="TabPFN",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "A pretrained transformer for tabular classification that uses "
            "in-context learning, requiring no gradient updates at training time."
        ),
        es=(
            "Un transformador pre-entrenado para clasificación tabular que usa "
            "aprendizaje en contexto, sin necesidad de actualizar gradientes "
            "al entrenar."
        ),
    )
    COLOR: str = "#5C6BC0"
    ICON: str = "Psychology"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to TabPFNClassifier.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent TabPFNClassifier.
            See the associated schema class for available keys and their defaults.
        """
        super().__init__(**kwargs)
