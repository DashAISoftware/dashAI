import os
import pathlib

import plotly.express as px
from beartype.typing import Any, Dict
from plotly.graph_objs import Figure
from plotly.io import read_json

from DashAI.back.core.schema_fields import bool_field, enum_field, schema_field
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Exploration, Explorer
from DashAI.back.exploration.base_explorer import BaseExplorer, BaseExplorerSchema


class BoxPlotSchema(BaseExplorerSchema):
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


class BoxPlotExplorer(BaseExplorer):
    """
    BoxPlotExplorer is an explorer that returns a box plot
    of selected columns of a dataset.
    """

    DISPLAY_NAME = "Box Plot"
    DESCRIPTION = (
        "BoxPlotExplorer is an explorer that returns a box plot "
        "of selected columns of a dataset."
    )

    SCHEMA = BoxPlotSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 1, "max": 2},
    }

    def __init__(self, **kwargs) -> None:
        self.horizontal = kwargs.get("horizontal", False)

        if kwargs.get("points") == "False":
            kwargs["points"] = False
        self.points = kwargs.get("points", "outliers")

        super().__init__(**kwargs)

    def launch_exploration(self, dataset: DashAIDataset, explorer_info: Explorer):
        _df = dataset.to_pandas()
        cols = [col["columnName"] for col in explorer_info.columns]

        if len(cols) == 1:
            fig = px.box(
                _df,
                x=cols[0] if self.horizontal else None,
                y=None if self.horizontal else cols[0],
                title=f"Boxplot of {cols[0]}",
                points=self.points,
            )
        elif len(cols) == 2:
            fig = px.box(
                _df,
                x=cols[1] if self.horizontal else cols[0],
                y=cols[0] if self.horizontal else cols[1],
                title=f"Boxplot of {cols[0]} vs {cols[1]}",
                points=self.points,
            )
        else:
            raise ValueError("BoxPlotExplorer can only handle 1 or 2 columns")

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
        filename = f"{explorer_info.id}.json"
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
