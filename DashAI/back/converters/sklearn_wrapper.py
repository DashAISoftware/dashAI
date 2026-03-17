from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Union

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_data_type import DashAIDataType

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class SklearnWrapper(BaseConverter, metaclass=ABCMeta):
    """Abstract class to define generic rules for sklearn transformers."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if hasattr(self, "set_output"):
            self.set_output(transform="pandas")

    @abstractmethod
    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """
        Each sklearn converter must implement this method to specify its output type.

        Parameters
        ----------
        column_name : str, optional
            The name of the column for which to get the output type.

        Returns
        -------
        DashAIDataType
            The DashAI data type for the output column.
        """
        raise NotImplementedError

    def fit(
        self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None
    ) -> BaseConverter:
        """
        Fit the sklearn transformer to the data.

        Parameters
        ----------
        x : DashAIDataset
            The input dataset to fit the transformer on.
        y : DashAIDataset or None, optional
            Target values for supervised transformers.

        Returns
        -------
        BaseConverter
            The fitted transformer instance.
        """
        x_pandas = x.to_pandas() if hasattr(x, "to_pandas") else x
        y_pandas = y.to_pandas() if y is not None and hasattr(y, "to_pandas") else y

        requires_y = hasattr(self, "_get_tags") and self._get_tags().get(
            "requires_y", False
        )

        if requires_y and y is None:
            raise ValueError("This transformer requires y for fitting")

        sklearn_cls = next(
            (
                cls
                for cls in type(self).__mro__
                if "sklearn" in cls.__module__
                and "DashAI" not in cls.__module__
                and "fit" in cls.__dict__
            ),
            None,
        )

        if sklearn_cls is None:
            raise RuntimeError(
                "No sklearn class with a 'fit' method found in the MRO. "
                "Ensure that your transformer inherits from a valid sklearn class."
            )
        fit_method = sklearn_cls.__dict__["fit"]
        if requires_y:
            fit_method(self, x_pandas, y_pandas)
        else:
            fit_method(self, x_pandas)

        return self

    def transform(
        self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None
    ) -> "DashAIDataset":
        """
        Transform the data using the fitted sklearn transformer.

        Parameters
        ----------
        x : DashAIDataset
            The input dataset to transform.
        y : DashAIDataset or None, optional
            Not used, present for API consistency.

        Returns
        -------
        DashAIDataset
            The transformed dataset with proper DashAI types.
        """
        import numpy as np
        import pandas as pd
        import pyarrow as pa

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        x_pandas = x.to_pandas() if hasattr(x, "to_pandas") else x

        sklearn_cls = next(
            (
                cls
                for cls in type(self).__mro__
                if "sklearn" in cls.__module__
                and "DashAI" not in cls.__module__
                and "transform" in cls.__dict__
            ),
            None,
        )

        if sklearn_cls is None:
            raise RuntimeError(
                "No sklearn class with a 'transform' method found in the "
                "inheritance hierarchy. Transformation cannot be performed."
            )
        x_new = sklearn_cls.__dict__["transform"](self, x_pandas)

        if isinstance(x_new, np.ndarray):
            columns = x_pandas.columns if hasattr(x_pandas, "columns") else None
            x_new = pd.DataFrame(x_new, columns=columns)

        converted_dataset = to_dashai_dataset(x_new)

        for col in converted_dataset.column_names:
            try:
                output_type = self.get_output_type(col)

                if isinstance(output_type, Categorical) and hasattr(self, "classes_"):
                    values = pa.array(self.classes_.tolist())
                    encoding = {v: i for i, v in enumerate(self.classes_)}
                    converted_dataset.types[col] = Categorical(
                        values=values, encoding=encoding, converted=True
                    )
                else:
                    converted_dataset.types[col] = output_type
            except NotImplementedError:
                pass

        return converted_dataset
