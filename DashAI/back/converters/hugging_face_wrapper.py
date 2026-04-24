from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Type

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.types.dashai_data_type import DashAIDataType

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class HuggingFaceWrapper(BaseConverter, metaclass=ABCMeta):
    """Abstract base wrapper for HuggingFace transformers."""

    def __init__(self, **kwargs):
        """Initialise the HuggingFace wrapper base class.

        Parameters
        ----------
        **kwargs : dict
            Keyword arguments forwarded to :class:`BaseConverter`.
        """
        super().__init__()

    @abstractmethod
    def _load_model(self):
        """Load the HuggingFace model and tokenizer."""
        raise NotImplementedError

    @abstractmethod
    def _process_batch(self, batch: "DashAIDataset") -> "DashAIDataset":
        """Process a single batch of records through the HuggingFace model.

        Parameters
        ----------
        batch : DashAIDataset
            A slice of the full dataset containing the rows to process.

        Returns
        -------
        DashAIDataset
            Transformed batch with model outputs.
        """
        raise NotImplementedError

    @abstractmethod
    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Return the DashAI data type produced for the given output column.

        Each concrete HuggingFace converter must implement this method to
        declare the type of the column it produces after transformation.

        Parameters
        ----------
        column_name : str or None, optional
            Name of the output column whose type is requested. Default ``None``.

        Returns
        -------
        DashAIDataType
            The DashAI type assigned to the output column.
        """
        raise NotImplementedError

    def fit(self, x: "DashAIDataset", y: "DashAIDataset" = None) -> Type[BaseConverter]:
        """Validate the input dataset and load the HuggingFace model.

        Checks that the dataset is non-empty and that all columns contain
        string data, then calls :meth:`_load_model` to download and cache
        the model weights if not already loaded.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset whose columns must all be string-typed.
        y : DashAIDataset or None, optional
            Ignored. Present for API compatibility. Default ``None``.

        Returns
        -------
        HuggingFaceWrapper
            The fitted converter instance (``self``).

        Raises
        ------
        ValueError
            If ``x`` is empty or any column does not contain string data.
        """
        if len(x) == 0:
            raise ValueError("Input dataset is empty")

        # Check that all columns contain string data
        for column in x.column_names:
            if not isinstance(x[0][column], str):
                raise ValueError(f"Column {column} must contain string data")

        # Load model if not already loaded
        self._load_model()

        return self

    def transform(
        self, x: "DashAIDataset", y: "DashAIDataset" = None
    ) -> "DashAIDataset":
        """Transform the input dataset by running inference in batches.

        Splits ``x`` into chunks of ``self.batch_size``, passes each chunk
        through :meth:`_process_batch`, concatenates the results, and assigns
        column types via :meth:`get_output_type`.

        Parameters
        ----------
        x : DashAIDataset
            The dataset to transform. Must have been fitted first.
        y : DashAIDataset or None, optional
            Ignored. Present for API compatibility. Default ``None``.

        Returns
        -------
        DashAIDataset
            Transformed dataset with output types set per column.
        """
        from datasets import concatenate_datasets

        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        all_results = []

        # Process in batches
        for i in range(0, len(x), self.batch_size):
            # Get the current batch
            batch = x.select(range(i, min(i + self.batch_size, len(x))))
            # Process the batch
            batch_results = self._process_batch(batch)
            all_results.append(batch_results)

        # Concatenate all results
        concatenated_dataset = concatenate_datasets(all_results)
        converted_dataset = DashAIDataset(concatenated_dataset.data.table)

        # Set types for each column using the converter's get_output_type method
        for col in converted_dataset.column_names:
            try:
                converted_dataset.types[col] = self.get_output_type(col)
            except NotImplementedError:
                print(
                    f"Warning: Converter {self.__class__.__name__} does not implement "
                    f"get_output_type. Column {col} type may not be properly set."
                )

        return converted_dataset
