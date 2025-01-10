from abc import ABCMeta, abstractmethod
from typing import Type
import pandas as pd
from DashAI.back.converters.base_converter import BaseConverter


class HuggingFaceWrapper(BaseConverter, metaclass=ABCMeta):
    """Abstract base wrapper for HuggingFace transformers."""

    def __init__(self, **kwargs):
        super().__init__()

    @abstractmethod
    def _load_model(self):
        """Load the HuggingFace model and tokenizer."""
        raise NotImplementedError

    @abstractmethod
    def _process_batch(self, batch: pd.DataFrame) -> pd.DataFrame:
        """Process a batch of data through the model."""
        raise NotImplementedError

    def fit(self, X: pd.DataFrame, y: pd.Series = None) -> Type[BaseConverter]:
        """Validate parameters and prepare for transformation."""
        if X.empty:
            raise ValueError("Input DataFrame is empty")

        # Check that all columns contain string data
        non_string_cols = [col for col in X.columns if X[col].dtype != object]
        if non_string_cols:
            raise ValueError(f"Columns {non_string_cols} must contain string data")

        # Load model if not already loaded
        self._load_model()

        return self

    def transform(self, X: pd.DataFrame, y: pd.Series = None) -> pd.DataFrame:
        """Transform the input data using the model."""
        all_results = []

        for i in range(0, len(X), self.batch_size):
            batch = X.iloc[i : i + self.batch_size]
            batch_results = self._process_batch(batch)
            all_results.append(batch_results)

        return pd.concat(all_results, axis=0, ignore_index=True)
