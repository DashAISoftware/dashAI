from typing import TYPE_CHECKING, Any, Dict, List

from DashAI.back.core.schema_fields import (
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.relationship_explorer import RelationshipExplorer

if TYPE_CHECKING:
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ScatterPlotSchema(BaseExplorerSchema):
    color_group: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        description=MultilingualString(
            en=("Column name or index used to group colored points."),
            es=("Nombre o índice de columna para agrupar puntos por color."),
        ),
        alias=MultilingualString(
            en="Color group column",
            es="Columna para grupo de color",
        ),
    )  # type: ignore
    simbol_group: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        description=MultilingualString(
            en=("Column name or index used to group point symbols."),
            es=("Nombre o índice de columna para agrupar símbolos de puntos."),
        ),
        alias=MultilingualString(
            en="Symbol group column",
            es="Columna para grupo de símbolo",
        ),
    )  # type: ignore
    point_size: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        description=MultilingualString(
            en=("Column name or index to set the size of each point."),
            es=("Nombre o índice de columna para definir el tamaño de cada punto."),
        ),
        alias=MultilingualString(en="Point size column", es="Columna tamaño punto"),
    )  # type: ignore


class ScatterPlotExplorer(RelationshipExplorer):
    """
    ScatterPlotExplorer is an explorer that returns a scatter plot
    of selected columns of a dataset.
    """

    DISPLAY_NAME = MultilingualString(en="Scatter Plot", es="Gráfico de Dispersión")
    DESCRIPTION = MultilingualString(
        en=(
            "Displays a scatter plot for two selected columns to explore their "
            "relationship."
        ),
        es=(
            "Muestra un gráfico de dispersión para dos columnas seleccionadas "
            "a fin de explorar su relación."
        ),
    )
    IMAGE_PREVIEW = "scatter_plot.png"

    SCHEMA = ScatterPlotSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
        "input_cardinality": {"exact": 2},
    }

    def __init__(self, **kwargs) -> None:
        self.color_column = kwargs.get("color_group")
        self.simbol_column = kwargs.get("simbol_group")
        self.size_column = kwargs.get("point_size")
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

        if self.size_column is not None:
            if isinstance(self.size_column, (int, float)):
                idx = self.size_column
                col = dataset_columns[idx]
                if col not in explorer_columns:
                    columns.append({"id": idx, "columnName": col})
            else:
                col = self.size_column
                if col not in explorer_columns:
                    columns.append({"columnName": col})
            self.size_column = col

        return super().prepare_dataset(loaded_dataset, columns)

    def launch_exploration(self, dataset: "DashAIDataset", explorer_info: Explorer):
        import plotly.express as px

        _df = dataset.to_pandas()
        cols = [col["columnName"] for col in explorer_info.columns]

        colorColumn = self.color_column if self.color_column in _df.columns else None
        simbolColumn = self.simbol_column if self.simbol_column in _df.columns else None
        sizeColumn = self.size_column if self.size_column in _df.columns else None

        fig = px.scatter(
            _df,
            x=cols[0],
            y=cols[1],
            color=colorColumn,
            symbol=simbolColumn,
            size=sizeColumn,
            title=f"Scatter Plot of {cols[0]} vs {cols[1]}",
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

        filename = f"{explorer_info.id}.pickle"
        path = Path(os.path.join(save_path, filename))

        result.write_json(path.as_posix())
        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        from plotly.io import read_json

        resultType = "plotly_json"
        config = {}

        result = read_json(exploration_path)
        result = result.to_json()

        return {"data": result, "type": resultType, "config": config}
