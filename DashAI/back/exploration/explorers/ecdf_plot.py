import enum
import os
import pathlib

import plotly.express as px
import plotly.io as pio
from beartype.typing import Any, Dict, List, Union
from plotly.graph_objs import Figure

from DashAI.back.core.schema_fields import (
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


class ECDFNorm(enum.Enum):
    NONE = "none"
    PERCENT = "percent"
    PROBABILITY = "probability"


class ECDFPlotSchema(BaseExplorerSchema):
    color_column: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        ("The column to use for coloring the ECDF plot."),
    )  # type: ignore
    facet_col: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        ("The column to use for faceting the ECDF plot in the column direction."),
    )  # type: ignore
    facet_row: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        ("The column to use for faceting the ECDF plot in the row direction."),
    )  # type: ignore
    ecdf_norm: schema_field(
        enum_field([e.value for e in ECDFNorm]),
        ECDFNorm.PROBABILITY.value,
        ("Specifies the type of normalization used for this ECDF plot."),
    )  # type: ignore


class ECDFPlotExplorer(BaseExplorer):
    """
    ECDFPlotExplorer is an explorer that creates an Empirical Cumulative
    Distribution Plot. It shows the proportion or count of observations
    falling below each unique value in the dataset.
    """

    DISPLAY_NAME = "Empirical Cumulative Distribution Plot"
    DESCRIPTION = (
        "The ECDF plot is a non-parametric way to explore the distribution of a "
        "variable. It shows the proportion or count of observations falling below "
        "each unique value in the dataset."
    )

    SCHEMA = ECDFPlotSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["float64", "float32"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 1},
    }

    def __init__(self, **kwargs) -> None:
        self.color_column: Union[str, int, None] = kwargs.get("color_column")
        self.facet_col: Union[str, int, None] = kwargs.get("facet_col")
        self.facet_row: Union[str, int, None] = kwargs.get("facet_row")
        self.ecdf_norm: ECDFNorm = ECDFNorm(kwargs.get("ecdf_norm"))
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

        if self.facet_col is not None:
            if isinstance(self.facet_col, int):
                idx = self.facet_col
                col = dataset_columns[idx]
                if col not in explorer_columns:
                    columns.append({"id": idx, "columnName": col})
            else:
                col = self.facet_col
                if col not in explorer_columns:
                    columns.append({"columnName": col})
            self.facet_col = col

        if self.facet_row is not None:
            if isinstance(self.facet_row, int):
                idx = self.facet_row
                col = dataset_columns[idx]
                if col not in explorer_columns:
                    columns.append({"id": idx, "columnName": col})
            else:
                col = self.facet_row
                if col not in explorer_columns:
                    columns.append({"columnName": col})
            self.facet_row = col

        return super().prepare_dataset(loaded_dataset, columns)

    def launch_exploration(self, dataset: DashAIDataset, explorer_info: Explorer):
        _df = dataset.to_pandas()
        columns = [col["columnName"] for col in explorer_info.columns]

        fig = px.ecdf(
            _df,
            x=columns[0] if len(columns) == 1 else columns,
            color=self.color_column,
            facet_col=self.facet_col,
            facet_row=self.facet_row,
            ecdfnorm=(
                self.ecdf_norm.value if self.ecdf_norm is not ECDFNorm.NONE else None
            ),
            title=(
                f"ECDF Plot of {len(columns)} columns"
                if len(columns) > 1
                else f"ECDF Plot of {columns[0]}"
            ),
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
