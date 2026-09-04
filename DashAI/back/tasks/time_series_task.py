"""Shared behaviour for the tasks that predict the future of a time series."""

from typing import TYPE_CHECKING, List, Union

from DashAI.back.tasks.base_task import BaseTask

if TYPE_CHECKING:
    from datasets import DatasetDict
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TimeSeriesTask(BaseTask):
    """Base class for the tasks that forecast a series forward in time.

    What every forecasting task shares is the date column and what it implies:
    the rows are a sequence in time rather than an unordered sample, the
    target is continuous so there are no labels to count, and a prediction
    needs no decoding because it is already a value on the scale of the
    series.

    What the subclasses differ in is the rest of the input contract, which is
    the whole of the difference between forecasting a series from its own
    history and forecasting it with explanatory variables alongside.
    """

    PREDICTS_FORWARD_ONLY: bool = True

    def prepare_for_task(
        self,
        dataset: Union["DatasetDict", "DashAIDataset"],
        input_columns: List[str],
        output_columns: List[str],
    ) -> "DashAIDataset":
        """Convert the dataset to a DashAIDataset and validate its types.

        Parameters
        ----------
        dataset : DatasetDict or DashAIDataset
            Dataset to prepare.
        input_columns : list of str
            The input columns, one of which is the date column.
        output_columns : list of str
            The single numeric column holding the series.

        Returns
        -------
        DashAIDataset
            Dataset with validated types, in date order.
        """
        prepared = super().prepare_for_task(dataset, input_columns, output_columns)
        return self._sort_by_date(prepared, self._date_column(prepared, input_columns))

    @staticmethod
    def _date_column(dataset: "DashAIDataset", input_columns: List[str]) -> str:
        """Find the date column among the selected inputs.

        Every forecasting task takes exactly one, but not necessarily first:
        with explanatory variables alongside, the user picks the columns in
        whatever order the file happens to have them.

        Parameters
        ----------
        dataset : DashAIDataset
            The validated dataset.
        input_columns : list of str
            The selected input columns.

        Returns
        -------
        str
            The name of the date column.
        """
        from DashAI.back.types.value_types import Date

        return next(
            name for name in input_columns if isinstance(dataset.types[name], Date)
        )

    @staticmethod
    def _sort_by_date(dataset: "DashAIDataset", date_column: str) -> "DashAIDataset":
        """Put the rows in date order.

        Everything downstream reads row order as time order and none of it
        checks: the temporal splitter carves its partitions by position, and
        the models hand their values to statsmodels in the order they arrive.
        A file that is not sorted by its date column therefore produces
        partitions that are not periods of time and a model fitted on a
        scrambled series, with nothing reporting a problem.

        This is the task's job rather than the splitter's. The splitter is
        handed the selected input columns, which on the windowed route through
        ``TimeSeriesWindowConverter`` are lag columns with no date among them.

        Sorting reads the format the column declares. Text order only matches
        time order for ISO layouts: as text, "01/02/2020" precedes
        "31/01/2020" while following it in time.

        Parameters
        ----------
        dataset : DashAIDataset
            The validated dataset.
        date_column : str
            The input column the task has already checked is a ``Date``.

        Returns
        -------
        DashAIDataset
            The same rows and types, ordered by date.
        """
        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
        from DashAI.back.types.date_utils import DEFAULT_DATE_FORMAT, parse_date_column

        date_format = (
            getattr(dataset.types[date_column], "format", None) or DEFAULT_DATE_FORMAT
        )
        frame = dataset.to_pandas()
        order = parse_date_column(frame[date_column], date_format).sort_values().index

        if list(order) == list(frame.index):
            return dataset

        return to_dashai_dataset(
            frame.loc[order].reset_index(drop=True), types=dict(dataset.types)
        )

    def process_predictions(
        self, dataset: "DashAIDataset", predictions: "ndarray", output_column: str
    ):
        """Return the forecast values unchanged.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset used for training.
        predictions : np.ndarray
            Predictions from the model.
        output_column : str
            Output column.

        Returns
        -------
        np.ndarray
            The predictions as they were produced. A forecast is already a
            number on the scale of the series, so there is nothing to decode.
        """
        return predictions

    def num_labels(self, dataset: "DashAIDataset", output_column: str) -> int | None:
        """Report that this task has no labels.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset used for training.
        output_column : str
            Output column.

        Returns
        -------
        int | None
            Always ``None``: the output is continuous, so there is no class
            count for a model to size itself against.
        """
        return None
