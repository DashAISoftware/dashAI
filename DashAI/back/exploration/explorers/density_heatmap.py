import os
import pathlib

import plotly.express as px
import plotly.io as pio
from beartype.typing import Any, Dict
from plotly.graph_objs import Figure

from DashAI.back.core.schema_fields import int_field, none_type, schema_field
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Exploration, Explorer
from DashAI.back.exploration.base_explorer import BaseExplorer, BaseExplorerSchema


class DensityHeatmapSchema(BaseExplorerSchema):
    nbinsx: schema_field(
        none_type(int_field(ge=1)),
        None,
        ("The number of bins along the x axis."),
    )  # type: ignore
    nbinsy: schema_field(
        none_type(int_field(ge=1)),
        None,
        ("The number of bins along the y axis."),
    )  # type: ignore


class DensityHeatmapExplorer(BaseExplorer):
    """
    DensityHeatmapExplorer is an explorer that returns a density heatmap
    of selected columns of a dataset.
    """

    DISPLAY_NAME = "Density Heatmap"
    DESCRIPTION = (
        "DensityHeatmapExplorer is an explorer that returns a density heatmap "
        "of selected columns of a dataset."
    )

    SCHEMA = DensityHeatmapSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"exact": 2},
    }

    def __init__(self, **kwargs) -> None:
        self.nbinsx = kwargs.get("nbinsx")
        self.nbinsy = kwargs.get("nbinsy")
        super().__init__(**kwargs)

    def launch_exploration(self, dataset: DashAIDataset, explorer_info: Explorer):
        _df = dataset.to_pandas()
        columns = [col["columnName"] for col in explorer_info.columns]

        fig = px.density_heatmap(
            _df,
            x=columns[0],
            y=columns[1],
            nbinsx=self.nbinsx,
            nbinsy=self.nbinsy,
            title=f"Density Heatmap of {columns[0]} and {columns[1]}",
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
        filename = f"{explorer_info.id}.json"
        path = pathlib.Path(os.path.join(save_path, filename))

        result.write_json(path.as_posix())
        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        resultType = "plotly_json"
        config = {}

        result = pio.read_json(exploration_path)
        result = result.to_json()

        return {"data": result, "type": resultType, "config": config}
