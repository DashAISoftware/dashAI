from abc import ABCMeta
from typing import Type

import pandas as pd

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)


class ImbalancedLearnWrapper(BaseConverter, metaclass=ABCMeta):
    """Generic wrapper for imbalanced-learn samplers (e.g., SMOTE, ADASYN)."""

    def __init__(self, **kwargs):
        # Initialize both BaseConverter and the sampler (via MRO)
        super(ImbalancedLearnWrapper, self).__init__(**kwargs)

    def fit(self, x: DashAIDataset, y: DashAIDataset) -> Type[BaseConverter]:
        """Fit the sampler using imbalanced-learn's fit_resample."""
        if y is None or y.to_pandas().empty:
            raise ValueError(
                "Imbalanced-learn samplers require a non-empty target dataset (y)."
            )

        X_df = x.to_pandas()
        y_pd_df = y.to_pandas()
        if y_pd_df.empty:
            raise ValueError(
                "Target dataset (y) resulted in an empty pandas DataFrame."
            )
        y_series = y_pd_df.iloc[:, 0]

        self.original_target_column_name_ = y.column_names[0]
        self.original_X_column_names_ = x.column_names

        # fit_resample is the standard API for samplers
        # It can return numpy arrays or pandas DataFrames/Series
        X_resampled_data, y_resampled_data = self.fit_resample(X_df, y_series)

        # Store as pandas objects for consistency
        self.X_resampled_df_ = pd.DataFrame(
            X_resampled_data, columns=self.original_X_column_names_
        )
        self.y_resampled_series_ = pd.Series(
            y_resampled_data, name=self.original_target_column_name_
        )

        self.fitted = True
        return self

    def transform(self, x: DashAIDataset, y: DashAIDataset = None) -> DashAIDataset:
        """Return just the resampled features (X_resampled)."""
        if not self.fitted:
            raise RuntimeError(f"{self.__class__.__name__} has not been fitted yet.")
        if not hasattr(self, "X_resampled_df_"):
            raise RuntimeError("Resampled X data not available. Call fit first.")

        # X_resampled_df_ should already have correct column names from fit
        return to_dashai_dataset(self.X_resampled_df_)
