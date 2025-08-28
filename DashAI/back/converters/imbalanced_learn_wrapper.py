from abc import ABCMeta
from typing import Type, Union

import numpy as np
import pandas as pd
import pyarrow as pa
from datasets.features import Features

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.job.base_job import JobError


class ImbalancedLearnWrapper(BaseConverter, metaclass=ABCMeta):
    """Generic wrapper for imbalanced-learn samplers (e.g., SMOTE, ADASYN)."""

    def __init__(self, **kwargs):
        super(ImbalancedLearnWrapper, self).__init__(**kwargs)
        self.fitted = False
        self._resampled_table: Union[pa.Table, None] = None
        self.original_X_column_names_: list = []
        self.original_target_column_name_: str = ""

    def changes_row_count(self) -> bool:
        return True

    def fit(self, x: DashAIDataset, y: DashAIDataset) -> Type[BaseConverter]:
        """
        Fit the sampler using imbalanced-learn's fit_resample and store the combined
        result.
        """
        if y is None or len(y) == 0:
            raise ValueError(
                "Imbalanced-learn samplers require a non-empty target dataset (y)."
            )

        X_df = x.to_pandas()
        y_series = y.to_pandas().iloc[:, 0]

        self.original_target_column_name_ = y.column_names[0]
        self.original_X_column_names_ = list(x.column_names)

        X_resampled_data, y_resampled_data = self.fit_resample(X_df, y_series)

        if isinstance(X_resampled_data, np.ndarray):
            X_resampled_df = pd.DataFrame(
                X_resampled_data, columns=self.original_X_column_names_
            )
        elif isinstance(X_resampled_data, pd.DataFrame):
            X_resampled_df = X_resampled_data
            X_resampled_df.columns = self.original_X_column_names_
        else:
            raise TypeError(
                (
                    "Unexpected type for X_resampled_data from imblearn: "
                    f"{type(X_resampled_data)}"
                )
            )

        if isinstance(y_resampled_data, np.ndarray):
            y_resampled_series = pd.Series(
                y_resampled_data, name=self.original_target_column_name_
            )
        elif isinstance(y_resampled_data, pd.Series):
            y_resampled_series = y_resampled_data
            y_resampled_series.name = self.original_target_column_name_
        else:
            raise TypeError(
                (
                    "Unexpected type for y_resampled_data from imblearn: "
                    f"{type(y_resampled_data)}"
                )
            )

        combined_df = pd.concat(
            [
                X_resampled_df.reset_index(drop=True),
                y_resampled_series.reset_index(drop=True),
            ],
            axis=1,
        )

        try:
            self._resampled_table = pa.Table.from_pandas(
                combined_df, preserve_index=False
            )
        except Exception as e:
            raise JobError(
                f"Failed to prepare resampled data as PyArrow Table: {e}"
            ) from e

        self.fitted = True
        return self

    def transform(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> DashAIDataset:
        """Return the stored resampled dataset (X and y combined)."""
        if not self.fitted:
            raise RuntimeError(f"{self.__class__.__name__} has not been fitted yet.")
        if self._resampled_table is None:
            raise RuntimeError("Resampled PyArrow Table not available. Call fit first.")

        try:
            resampled_features = Features.from_arrow_schema(
                self._resampled_table.schema
            )
            return DashAIDataset(
                table=self._resampled_table, features=resampled_features, splits={}
            )
        except Exception as e:
            raise JobError(
                f"Failed to create DashAIDataset from resampled data: {e}"
            ) from e
