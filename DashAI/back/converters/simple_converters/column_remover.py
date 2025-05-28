from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
)


class ColumnRemoverSchema(BaseSchema):
    pass


class ColumnRemover(BaseConverter):
    """
    Converter that removes specified columns from the dataset.
    This converter uses the scope columns defined in the converter job UI.
    The columns selected in the scope will be the ones removed from the dataset.
    """

    SCHEMA = ColumnRemoverSchema
    DESCRIPTION = "Removes the columns selected in scope from the dataset."

    def __init__(self):
        super().__init__()
        self.columns = []

    def fit(self, x: DashAIDataset, y: DashAIDataset = None) -> "ColumnRemover":
        """
        Fit the column remover.

        The columns to be removed are determined by the columns passed to x,
        which are selected by scope in converter_job.
        """
        self.columns = x.column_names
        return self

    def transform(self, x: DashAIDataset, y: DashAIDataset = None) -> DashAIDataset:
        """
        Remove the columns that were selected via scope.
        """
        missing = [col for col in self.columns if col not in x.column_names]
        if missing:
            raise ValueError(
                f"Cannot remove columns that do not exist in the dataset: {missing}"
            )

        return x.remove_columns(self.columns)
