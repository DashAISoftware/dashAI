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


class HistFunc(enum.Enum):
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class HistNorm(enum.Enum):
    NONE = ""
    PERCENT = "percent"
    PROBABILITY = "probability"
    DENSITY = "density"
    PROBABILITY_DENSITY = "probability density"


class HistogramPlotSchema(BaseExplorerSchema):
    nbins: schema_field(
        none_type(int_field(ge=1)),
        None,
        ("The number of bins to use for the histogram."),
    )  # type: ignore
    histfunc: schema_field(
        enum_field([e.value for e in HistFunc]),
        HistFunc.COUNT.value,
        ("Specifies the binning function used for this histogram trace."),
    )  # type: ignore
    histnorm: schema_field(
        enum_field([e.value for e in HistNorm]),
        HistNorm.NONE.value,
        ("Specifies the type of normalization used for this histogram trace."),
    )  # type: ignore
    color_group: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        ("The columnName or columnIndex to take for grouping colored points."),
    )  # type: ignore
    pattern_group: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        ("The columnName or columnIndex to take for grouping pattern of the points."),
    )  # type: ignore


class HistogramPlotExplorer(BaseExplorer):
    """
    HistogramPlotExplorer is an explorer that returns a density heatmap
    of a selected column of a dataset.
    """

    DISPLAY_NAME = "Histogram Plot"
    DESCRIPTION = (
        "HistogramPlotExplorer is an explorer that returns a density heatmap "
        "of a selected column of a dataset."
    )

    SCHEMA = HistogramPlotSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"exact": 1},
    }

    def __init__(self, **kwargs) -> None:
        self.nbins: Union[int, None] = kwargs.get("nbins")
        self.histfunc: HistFunc = HistFunc(kwargs.get("histfunc"))
        self.histnorm: HistNorm = HistNorm(kwargs.get("histnorm"))
        self.color_column: Union[str, int, None] = kwargs.get("color_group")
        self.pattern_column: Union[str, int, None] = kwargs.get("pattern_group")
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

        if self.pattern_column is not None:
            if isinstance(self.pattern_column, int):
                idx = self.pattern_column
                col = dataset_columns[idx]
                if col not in explorer_columns:
                    columns.append({"id": idx, "columnName": col})
            else:
                col = self.pattern_column
                if col not in explorer_columns:
                    columns.append({"columnName": col})
            self.pattern_column = col

        return super().prepare_dataset(loaded_dataset, columns)

    def launch_exploration(self, dataset: DashAIDataset, explorer_info: Explorer):
        _df = dataset.to_pandas()
        columns = [col["columnName"] for col in explorer_info.columns]

        fig = px.histogram(
            _df,
            x=columns[0],
            nbins=self.nbins,
            histnorm=self.histnorm.value,
            histfunc=self.histfunc.value,
            color=self.color_column,
            pattern_shape=self.pattern_column,
            title=f"Histogram of {columns[0]}",
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
