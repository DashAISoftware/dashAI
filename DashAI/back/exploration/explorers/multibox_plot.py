import os
import pathlib

from beartype.typing import Any, Dict, List

from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.multidimensional_explorer import MultidimensionalExplorer


class MultiColumnBoxPlotSchema(BaseExplorerSchema):
    horizontal: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en=("If True, the box plot will be horizontal; otherwise vertical."),
            es=(
                "Si es True, el diagrama de caja será horizontal; en caso "
                "contrario, vertical."
            ),
        ),
        alias=MultilingualString(
            en="Horizontal plot",
            es="Gráfico horizontal",
        ),
    )  # type: ignore
    points: schema_field(
        enum_field(["all", "outliers", "False"]),
        "outliers",
        description=MultilingualString(
            en=(
                "One of 'all', 'outliers', or 'False'. Determines which points "
                "are shown."
            ),
            es=(
                "Una de 'all', 'outliers' o 'False'. Determina qué puntos se muestran."
            ),
        ),
        alias=MultilingualString(
            en="Points shown",
            es="Puntos mostrados",
        ),
    )  # type: ignore
    opposite_axis: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        description=MultilingualString(
            en=("Column name or index to use for the opposite axis."),
            es=("Nombre o índice de columna para el eje opuesto."),
        ),
        alias=MultilingualString(en="Opposite axis", es="Eje opuesto"),
    )  # type: ignore


class MultiColumnBoxPlotExplorer(MultidimensionalExplorer):
    """
    MultiColumnBoxPlotExplorer is an explorer that returns a figure with a box plot
    of multiple columns of a dataset in a single axis.

    The other axis is selected through the opposite_axis parameter.
    """

    DISPLAY_NAME = MultilingualString(
        en="Multiple Column Box Plot",
        es="Diagrama de Caja Multicolumna",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Shows a box plot for multiple columns on one axis, using another "
            "column as the opposite axis (if provided)."
        ),
        es=(
            "Muestra un diagrama de caja para múltiples columnas en un eje, "
            "usando otra columna como eje opuesto (si se proporciona)."
        ),
    )
    IMAGE_PREVIEW = "multi_column_box_plot.png"

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
        import plotly.graph_objects as go

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

    def save_notebook(
        self,
        __notebook_info__: Notebook,
        explorer_info: Explorer,
        save_path: pathlib.Path,
        result: Any,
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
        from plotly.io import read_json

        result = read_json(exploration_path)
        result = result.to_json()

        return {"data": result, "type": resultType, "config": config}
