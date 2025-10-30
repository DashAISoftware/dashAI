from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.converters.category.basic_preprocessing import (
    BasicPreprocessingConverter,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)


class NanRemoverSchema(BaseSchema):
    pass


class NanRemover(BasicPreprocessingConverter, BaseConverter):
    """
    A converter that removes rows with NaN values from the dataset.
    Only the columns selected in the scope are used to determine which
    rows to drop; other columns are deleted entirely.
    """

    SCHEMA = NanRemoverSchema
    DESCRIPTION = (
        "Removes the rows with NaN values from the dataset. "
        "Keep in mind that this converter will also remove "
        "columns not selected in the scope."
    )
    SHORT_DESCRIPTION = "Removes the rows with NaN values from the dataset."
    DISPLAY_NAME = "NaN Remover"
    CATEGORY = "Basic Preprocessing"
    IMAGE_PREVIEW = "nan_remover.png"

    def __init__(self):
        super().__init__()
        self.columns = []

    def fit(self, x: DashAIDataset, y: DashAIDataset = None) -> "NanRemover":
        """
        Fit the NaN remover.

        The columns to be affected are determined by the columns passed to x,
        which are selected by scope in converter_job.
        """
        self.columns = x.column_names
        return self

    def transform(self, x: DashAIDataset, y: DashAIDataset = None) -> DashAIDataset:
        """
        Remove the nan rows from the columns selected in the scope.
        """
        missing = [col for col in self.columns if col not in x.column_names]
        if missing:
            raise ValueError(
                (
                    "Cannot remove NaN from columns that do not exist "
                    "in the dataset: {}"
                ).format(missing)
            )

        dataset = x.to_pandas()
        mask = dataset[self.columns].notna().all(axis=1)

        cleaned_dataset = dataset[mask]

        return to_dashai_dataset(cleaned_dataset)

    def changes_row_count(self) -> bool:
        """
        Indicates that the converter changes the number of rows in the dataset.
        """
        return True
