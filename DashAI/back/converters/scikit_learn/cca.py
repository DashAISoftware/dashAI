from sklearn.cross_decomposition import CCA as CCAOPERATION

from DashAI.back.converters.category.advanced_preprocessing import (
    AdvancedPreprocessingConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float, Integer


class CCASchema(BaseSchema):
    """Configuration schema for the CCA converter.

    Defines and validates the hyperparameters passed to
    ``sklearn.cross_decomposition.CCA``.
    """

    n_components: schema_field(
        int_field(ge=1),
        2,
        description=MultilingualString(
            en="Number of components to keep.",
            es="Número de componentes a conservar.",
        ),
    )  # type: ignore
    scale: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Whether to scale the data.",
            es="Si se deben escalar los datos.",
        ),
    )  # type: ignore
    max_iter: schema_field(
        int_field(ge=1),
        500,
        description=MultilingualString(
            en="Maximum number of iterations to perform.",
            es="Número máximo de iteraciones a realizar.",
        ),
    )  # type: ignore
    tol: schema_field(
        float_field(ge=0.0),
        1e-6,
        description=MultilingualString(
            en="Tolerance for the stopping condition.",
            es="Tolerancia para la condición de parada.",
        ),
    )  # type: ignore
    copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Whether to copy X and Y or perform in-place normalization.",
            es="Si copiar X e Y o normalizar in situ.",
        ),
    )  # type: ignore


class CCA(AdvancedPreprocessingConverter, SklearnWrapper, CCAOPERATION):
    """Find linear projections of two datasets that are maximally correlated.

    Canonical Correlation Analysis (CCA) seeks pairs of linear combinations
    (canonical variates) u_i = X w_i and v_i = Y c_i such that the correlation
    between u_i and v_i is maximised, subject to the variates being uncorrelated
    with all previous pairs. The result is ``n_components`` pairs of weight
    vectors that define a shared latent space capturing the cross-covariance
    structure of the two views X and Y.

    CCA is used in multi-view learning, neuroscience (relating brain signals to
    stimuli), and natural language processing (aligning bilingual embeddings). It
    also subsumes reduced-rank regression and is equivalent to "Mode B" Partial
    Least Squares when the regularisation is set to zero.

    Key properties:

    - Supervised: both X and Y are required at fit time.
    - The ``scale`` flag standardises each block to zero mean and unit variance
      before fitting, which is strongly recommended when the two views have
      different measurement scales.
    - Solved by iterative deflation; ``max_iter`` and ``tol`` control
      convergence.
    - Output dimensionality is ``n_components`` for each view.

    Wraps scikit-learn's ``CCA``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.cross_decomposition.CCA.html
    - [2] Hotelling, H. (1936). "Relations between two sets of variates."
        Biometrika, 28(3/4), 321-377.
    """

    TAGS = ["dim-reduction", "supervised", "linear"]
    SCHEMA = CCASchema
    DESCRIPTION = MultilingualString(
        en="Canonical Correlation Analysis, also known as 'Mode B' PLS.",
        es="Análisis de Correlación Canónica, también conocido como PLS 'Modo B'.",
    )
    DISPLAY_NAME = MultilingualString(en="CCA", es="CCA")

    metadata = {
        "allowed_types": [Float, Integer],
        "allowed_dtypes": [],
    }

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Return the DashAI data type produced by this converter for a column.

        Parameters
        ----------
        column_name : str, optional
            Not used; all output columns share the
            same type. Defaults to None.

        Returns
        -------
        DashAIDataType
            A Float type backed by ``pyarrow.float64()``.
        """
        import pyarrow as pa

        return Float(arrow_type=pa.float64())
