from abc import ABCMeta, abstractmethod
from typing import Type

from datasets import concatenate_datasets

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
)


class HuggingFaceWrapper(BaseConverter, metaclass=ABCMeta):
    """Abstract base wrapper for HuggingFace transformers."""

    def __init__(self, **kwargs):
        super().__init__()

    @abstractmethod
    def _load_model(self):
        """Load the HuggingFace model and tokenizer."""
        raise NotImplementedError

    @abstractmethod
    def _process_batch(self, batch: DashAIDataset) -> DashAIDataset:
        """Process a batch of data through the model."""
        raise NotImplementedError

    def fit(self, x: DashAIDataset, y: DashAIDataset = None) -> Type[BaseConverter]:
        """Validate parameters and prepare for transformation."""
        if len(x) == 0:
            raise ValueError("Input dataset is empty")

        # Check that all columns contain string data
        for column in x.column_names:
            if not isinstance(x[0][column], str):
                raise ValueError(f"Column {column} must contain string data")

        # Load model if not already loaded
        self._load_model()

        return self

    def transform(self, x: DashAIDataset, y: DashAIDataset = None) -> DashAIDataset:
        """Transform the input data using the model."""
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
        return DashAIDataset(concatenated_dataset.data.table)
