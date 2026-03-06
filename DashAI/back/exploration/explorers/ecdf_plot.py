from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Union

from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.distribution_explorer import DistributionExplorer

if TYPE_CHECKING:
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ECDFNorm(Enum):
    NONE = "none"
    PERCENT = "percent"
    PROBABILITY = "probability"


class ECDFPlotSchema(BaseExplorerSchema):
    color_column: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        description=MultilingualString(
            en=("Column used to color the ECDF plot."),
            es=("Columna usada para colorear el gráfico ECDF."),
        ),
        alias=MultilingualString(en="Color column", es="Columna de color"),
    )  # type: ignore
    facet_col: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        description=MultilingualString(
            en=("Column used to facet the ECDF plot by columns."),
            es=("Columna usada para facetar el gráfico ECDF por columnas."),
        ),
        alias=MultilingualString(en="Facet column", es="Facetear por columnas"),
    )  # type: ignore
    facet_row: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        description=MultilingualString(
            en=("Column used to facet the ECDF plot by rows."),
            es=("Columna usada para facetar el gráfico ECDF por filas."),
        ),
        alias=MultilingualString(en="Facet row", es="Facetear por filas"),
    )  # type: ignore
    ecdf_norm: schema_field(
        enum_field([e.value for e in ECDFNorm]),
        ECDFNorm.PROBABILITY.value,
        description=MultilingualString(
            en=("Type of normalization used for the ECDF plot."),
            es=("Tipo de normalización usada en el gráfico ECDF."),
        ),
        alias=MultilingualString(en="ECDF normalization", es="Normalización ECDF"),
    )  # type: ignore


class ECDFPlotExplorer(DistributionExplorer):
    """
    ECDFPlotExplorer is an explorer that creates an Empirical Cumulative
    Distribution Plot. It shows the proportion or count of observations
    falling below each unique value in the dataset.
    """

    DISPLAY_NAME = MultilingualString(
        en="Empirical Cumulative Distribution Plot",
        es="Gráfico ECDF (Distribución Acumulada Empírica)",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Non-parametric plot showing the proportion or count of "
            "observations below each unique value."
        ),
        es=(
            "Gráfico no paramétrico que muestra la proporción o el conteo de "
            "observaciones por debajo de cada valor único."
        ),
    )
    IMAGE_PREVIEW = "ecdf_plot.png"

    SCHEMA = ECDFPlotSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["float64", "float32", "int64"],
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
        self, loaded_dataset: "DashAIDataset", columns: List[Dict[str, Any]]
    ) -> "DashAIDataset":
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

    def launch_exploration(self, dataset: "DashAIDataset", explorer_info: Explorer):
        import plotly.express as px

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

    def save_notebook(
        self,
        __notebook_info__: Notebook,
        explorer_info: Explorer,
        save_path: "Path",
        result: Any,
    ) -> str:
        import os
        from pathlib import Path

        filename = f"{explorer_info.id}.json"
        path = Path(os.path.join(save_path, filename))

        result.write_json(path.as_posix())
        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        import plotly.io as pio

        resultType = "plotly_json"
        config = {}

        result = pio.read_json(exploration_path)
        result = result.to_json()

        return {"data": result, "type": resultType, "config": config}
