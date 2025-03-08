import os
import pathlib

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from beartype.typing import Any, Dict, Union

from DashAI.back.core.schema_fields import bool_field, int_field, schema_field
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Exploration, Explorer
from DashAI.back.exploration.base_explorer import BaseExplorer, BaseExplorerSchema


class CovarianceMatrixExplorerSchema(BaseExplorerSchema):
    min_periods: schema_field(
        int_field(gt=0),
        1,
        (
            "The minimum number of observations required per pair of columns to"
            " have a valid result."
        ),
    )  # type: ignore
    delta_degree_of_freedom: schema_field(
        int_field(gt=0),
        1,
        (
            "The delta degree of freedom to use when calculating the covariance matrix."
            "Only used if numeric_only is True."
        ),
    )  # type: ignore
    numeric_only: schema_field(
        bool_field(),
        True,
        (
            "If True, only include numeric columns when calculating correlation."
            "If False, all columns are included."
        ),
    )  # type: ignore
    plot: schema_field(
        bool_field(),
        True,
        ("If True, the result will be plotted."),
    )  # type: ignore


class CovarianceMatrixExplorer(BaseExplorer):
    """
    CovarianceExplorer is an explorer that returns the covariance matrix of the dataset.

    Its result is a heatmap by default, but can also be returned as a tabular result.
    """

    DISPLAY_NAME = "Covariance Matrix"
    DESCRIPTION = (
        "CovarianceExplorer is an explorer that returns the covariance matrix "
        "of the dataset."
        "\n"
        "Its result is a heatmap by default, "
        "but can also be returned as a tabular result."
    )

    SCHEMA = CovarianceMatrixExplorerSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 2},
    }

    def __init__(self, **kwargs) -> None:
        self.ddof = kwargs.get("delta_degree_of_freedom")
        self.min_periods = kwargs.get("min_periods")
        self.numeric_only = kwargs.get("numeric_only")
        self.plot = kwargs.get("plot")
        super().__init__(**kwargs)

    def launch_exploration(
        self, dataset: DashAIDataset, explorer_info: Explorer
    ) -> Union[pd.DataFrame, go.Figure]:
        result = dataset.to_pandas().cov(
            min_periods=self.min_periods,
            ddof=self.ddof,
            numeric_only=self.numeric_only,
        )

        if self.plot:
            result = px.imshow(
                result,
                text_auto=True,
                aspect="auto",
                title=f"Covariance Matrix of {len(explorer_info.columns)} columns",
            )
            if explorer_info.name is not None and explorer_info.name != "":
                result.update_layout(title=f"{explorer_info.name}")

        return result

    def save_exploration(
        self,
        __exploration_info__: Exploration,
        explorer_info: Explorer,
        save_path: pathlib.Path,
        result: Union[pd.DataFrame, go.Figure],
    ) -> str:
        filename = f"{explorer_info.id}.json"
        path = pathlib.Path(os.path.join(save_path, filename))

        if self.plot:
            assert isinstance(result, go.Figure)
            result.write_json(path)
        else:
            assert isinstance(result, pd.DataFrame)
            result.to_json(path)
        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self.plot:
            resultType = "plotly_json"
            path = pathlib.Path(exploration_path)
            result = pio.read_json(path).to_json()
            return {"type": resultType, "data": result, "config": {}}

        resultType = "tabular"
        orientation = options.get("orientation", "dict")
        config = {"orient": orientation}

        path = pathlib.Path(exploration_path)
        result = (
            pd.read_json(path).replace({np.nan: None}).T.to_dict(orient=orientation)
        )
        return {"type": resultType, "data": result, "config": config}
