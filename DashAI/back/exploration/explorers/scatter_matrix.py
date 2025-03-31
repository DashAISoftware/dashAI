import os
import pathlib

import plotly.express as px
import plotly.io as pio
from beartype.typing import Any, Dict, List
from plotly.graph_objs import Figure

from DashAI.back.core.schema_fields import (
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


class ScatterMatrixSchema(BaseExplorerSchema):
    color_group: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        ("The columnName or columnIndex to take for grouping colored points."),
    )  # type: ignore
    simbol_group: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        ("The columnName or columnIndex to take for grouping simbol of the points."),
    )  # type: ignore


class ScatterMatrixExplorer(BaseExplorer):
    """
    ScatterMatrixExplorer is an explorer that returns a scatter matrix plot
    of selected columns of a dataset.
    """

    DISPLAY_NAME = "Multiple Scatter Plot"
    DESCRIPTION = (
        "ScatterMatrixExplorer is an explorer that returns a scatter matrix plot "
        "of selected columns of a dataset. Multiple scatter plots are generated "
        "for each pair of columns. The diagonal plots are histograms of the columns. "
    )

    SCHEMA = ScatterMatrixSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 2},
    }

    def __init__(self, **kwargs) -> None:
        self.color_column = kwargs.get("color_group")
        self.simbol_column = kwargs.get("simbol_group")
        super().__init__(**kwargs)

    def prepare_dataset(
        self, loaded_dataset: DashAIDataset, columns: List[Dict[str, Any]]
    ) -> DashAIDataset:
        explorer_columns = [col["columnName"] for col in columns]
        dataset_columns = loaded_dataset.column_names

        if self.color_column is not None:
            if isinstance(self.color_column, int):
                idx = self.color_column
                col = dataset_columns[idx]
                if col not in explorer_columns:
                    columns.append({"id": idx, "columnName": col})
            else:
                col = self.color_column
                if col not in explorer_columns:
                    columns.append({"columnName": col})
            self.color_column = col

        if self.simbol_column is not None:
            if isinstance(self.simbol_column, int):
                idx = self.simbol_column
                col = dataset_columns[idx]
                if col not in explorer_columns:
                    columns.append({"id": idx, "columnName": col})
            else:
                col = self.simbol_column
                if col not in explorer_columns:
                    columns.append({"columnName": col})
            self.simbol_column = col

        return super().prepare_dataset(loaded_dataset, columns)

    def launch_exploration(self, dataset: DashAIDataset, explorer_info: Explorer):
        _df = dataset.to_pandas()
        dimensions = [col["columnName"] for col in explorer_info.columns]

        colorColumn = self.color_column if self.color_column in _df.columns else None
        simbolColumn = self.simbol_column if self.simbol_column in _df.columns else None

        fig = px.scatter_matrix(
            _df,
            dimensions=dimensions,
            color=colorColumn,
            symbol=simbolColumn,
            title=f"Scatter Matrix of {len(dimensions)} columns",
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
