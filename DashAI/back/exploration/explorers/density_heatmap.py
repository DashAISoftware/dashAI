import os
import pathlib

import plotly.express as px
from beartype.typing import Any, Dict
from plotly.graph_objs import Figure

from DashAI.back.core.schema_fields import int_field, none_type, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.relationship_explorer import RelationshipExplorer


class DensityHeatmapSchema(BaseExplorerSchema):
    nbinsx: schema_field(
        none_type(int_field(ge=1)),
        None,
        description=MultilingualString(
            en=("Number of bins along the x axis."),
            es=("Número de bins a lo largo del eje x."),
        ),
        alias=MultilingualString(en="Bins (x)", es="Bins (x)"),
    )  # type: ignore
    nbinsy: schema_field(
        none_type(int_field(ge=1)),
        None,
        description=MultilingualString(
            en=("Number of bins along the y axis."),
            es=("Número de bins a lo largo del eje y."),
        ),
        alias=MultilingualString(en="Bins (y)", es="Bins (y)"),
    )  # type: ignore


class DensityHeatmapExplorer(RelationshipExplorer):
    """
    DensityHeatmapExplorer is an explorer that returns a density heatmap
    of selected columns of a dataset.
    """

    DISPLAY_NAME = MultilingualString(
        en="Density Heatmap",
        es="Mapa de Calor de Densidad",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Returns a density heatmap for two selected columns to visualize the "
            "joint distribution."
        ),
        es=(
            "Devuelve un mapa de calor de densidad para dos columnas "
            "seleccionadas y visualizar su distribución conjunta."
        ),
    )
    IMAGE_PREVIEW = "density_heatmap.png"

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

    def save_notebook(
        self,
        __notebook_info__: Notebook,
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

        with open(exploration_path, "r", encoding="utf-8") as f:
            result = f.read()

        return {"data": result, "type": resultType, "config": config}
