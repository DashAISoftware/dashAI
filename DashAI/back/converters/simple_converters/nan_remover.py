from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.converters.category.basic_preprocessing import (
    BasicPreprocessingConverter,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Text

NULL_VALUES = {
    "none",
    "null",
    "nan",
    "na",
    "n/a",
    "",
    "missing",
    "undefined",
    "<na>",
    "nil",
    ".",
}


class NanRemoverSchema(BaseSchema):
    pass


class NanRemover(BasicPreprocessingConverter, BaseConverter):
    """
    A converter that removes rows with NaN values from the dataset.
    Only the columns selected in the scope are used to determine which
    rows to drop; other columns are deleted entirely.
    """

    SCHEMA = NanRemoverSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Removes the rows with NaN values from the dataset. Keep in mind that "
            "this converter will also remove columns not selected in the scope."
        ),
        es=(
            "Elimina las filas con valores NaN del conjunto de datos. Ten en "
            "cuenta que este convertidor también eliminará las columnas no "
            "seleccionadas en el alcance."
        ),
    )
    SHORT_DESCRIPTION = MultilingualString(
        en="Removes the rows with NaN values from the dataset.",
        es="Elimina las filas con valores NaN del conjunto de datos.",
    )
    DISPLAY_NAME = MultilingualString(en="NaN Remover", es="Removedor de NaN")
    IMAGE_PREVIEW = "nan_remover.png"

    metadata = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
    }

    def __init__(self):
        super().__init__()
        self.columns = []
        self.column_types = {}

    def fit(self, x: DashAIDataset, y: DashAIDataset = None) -> "NanRemover":
        """
        Fit the NaN remover.

        The columns to be affected are determined by the columns passed to x,
        which are selected by scope in converter_job.
        """
        self.columns = x.column_names
        self.column_types = x.types.copy()
        return self

    def _is_null_value(self, value) -> bool:
        """Check if a value should be treated as null."""
        import numpy as np

        if value is None:
            return True
        if isinstance(value, float) and np.isnan(value):
            return True
        value_str = str(value).lower().strip()
        return value_str in NULL_VALUES

    def transform(self, x: DashAIDataset, y: DashAIDataset = None) -> DashAIDataset:
        """
        Remove the nan rows from the columns selected in the scope.
        Also handles string representations of null values like "None", "nan", etc.
        """
        import numpy as np

        missing = [col for col in self.columns if col not in x.column_names]
        if missing:
            raise ValueError(
                (
                    "Cannot remove NaN from columns that do not exist "
                    "in the dataset: {}"
                ).format(missing)
            )

        dataset = x.to_pandas()

        mask = np.ones(len(dataset), dtype=bool)

        for col in self.columns:
            col_type = self.column_types.get(col)
            series = dataset[col]

            col_mask = ~series.isna()

            if isinstance(col_type, Categorical) or series.dtype == object:
                string_null_mask = ~series.apply(self._is_null_value)
                col_mask = col_mask & string_null_mask

            mask = mask & col_mask

        cleaned_dataset = dataset[mask]

        preserved_types = {
            col: self.column_types[col]
            for col in cleaned_dataset.columns
            if col in self.column_types
        }

        return to_dashai_dataset(cleaned_dataset, types=preserved_types)

    def changes_row_count(self) -> bool:
        """
        Indicates that the converter changes the number of rows in the dataset.
        """
        return True

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """
        This converter removes rows with NaN, doesn't change column types.
        Return the original type if available.
        """
        import pyarrow as pa

        if column_name and column_name in self.column_types:
            return self.column_types[column_name]
        return Text(arrow_type=pa.string())
