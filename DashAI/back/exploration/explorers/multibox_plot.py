import os
import pathlib

import plotly.graph_objects as go
from beartype.typing import Any, Dict, List
from plotly.graph_objs import Figure
from plotly.io import read_json

from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Exploration, Explorer
from DashAI.back.exploration.base_explorer import BaseExplorer, BaseExplorerSchema


class MultiColumnBoxPlotSchema(BaseExplorerSchema):
    horizontal: schema_field(
        bool_field(),
        False,
        ("If True, the box plot will be horizontal, otherwise vertical."),
    )  # type: ignore
    points: schema_field(
        enum_field(["all", "outliers", "False"]),
        "outliers",
        ("One of 'all', 'outliers', or 'False'. Determines which points are shown."),
    )  # type: ignore
    opposite_axis: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        ("The columnName or columnIndex to take for the opposite axis."),
    )  # type: ignore


class MultiColumnBoxPlotExplorer(BaseExplorer):
    """
    MultiColumnBoxPlotExplorer is an explorer that returns a figure with a box plot
    of multiple columns of a dataset in a single axis.

    The other axis is selected through the opposite_axis parameter.
    """

    DISPLAY_NAME = "Multiple Column Box Plot"
    DESCRIPTION = (
        "MultiColumnBoxPlotExplorer is an explorer that returns a figure with a box "
        "plot of multiple columns of a dataset in a single axis. "
        "The other axis is selected through the opposite_axis parameter."
    )

    SCHEMA = MultiColumnBoxPlotSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 1},
    }

    def __init__(self, **kwargs) -> None:
        self.horizontal = kwargs.get("horizontal", False)

        if kwargs.get("points") == "False":
            kwargs["points"] = False
        self.points = kwargs.get("points", "outliers")
        self.opposite_axis = kwargs.get("opposite_axis")

        super().__init__(**kwargs)

    def prepare_dataset(
        self, loaded_dataset: DashAIDataset, columns: List[Dict[str, Any]]
    ) -> DashAIDataset:
        explorer_columns = [col["columnName"] for col in columns]
        dataset_columns = loaded_dataset.column_names

        if self.opposite_axis is not None and self.opposite_axis != "":
            if isinstance(self.opposite_axis, int):
                idx = self.opposite_axis
                col = dataset_columns[idx]
                if col not in explorer_columns:
                    columns.append({"id": idx, "columnName": col})
            else:
                col = self.opposite_axis
                if col not in explorer_columns:
                    columns.append({"columnName": col})
            self.opposite_axis = col
        else:
            self.opposite_axis = None

        return super().prepare_dataset(loaded_dataset, columns)

    def launch_exploration(self, dataset: DashAIDataset, explorer_info: Explorer):
        _df = dataset.to_pandas()
        cols = [col["columnName"] for col in explorer_info.columns]

        opposite_axis = (
            _df[self.opposite_axis] if self.opposite_axis is not None else None
        )

        fig = go.Figure()
        for col in cols:
            fig.add_trace(
                go.Box(
                    x=_df[col] if self.horizontal else opposite_axis,
                    y=opposite_axis if self.horizontal else _df[col],
                    name=col,
                    boxpoints=self.points,
                )
            )

        fig.update_layout(
            title=f"Boxplot of {len(cols)} columns",
            xaxis_title=None if self.horizontal else self.opposite_axis,
            yaxis_title=self.opposite_axis if self.horizontal else None,
            boxmode="group",
        )

        if explorer_info.name is not None and explorer_info.name != "":
            fig.update_layout(title=f"{explorer_info.name}")

        return fig

    def save_exploration(
        self,
        __exploration_info__: Exploration,
        explorer_info: Explorer,
        save_path: pathlib.Path,
        result: Figure,
    ) -> str:
        filename = f"{explorer_info.id}.pickle"
        path = pathlib.Path(os.path.join(save_path, filename))

        result.write_json(path.as_posix())

        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        resultType = "plotly_json"
        config = {}

        result = read_json(exploration_path)
        result = result.to_json()

        return {"data": result, "type": resultType, "config": config}
