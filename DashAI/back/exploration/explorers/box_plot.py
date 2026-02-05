import os
import pathlib

from beartype.typing import Any, Dict

from DashAI.back.core.schema_fields import bool_field, enum_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.distribution_explorer import DistributionExplorer


class BoxPlotSchema(BaseExplorerSchema):
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


class BoxPlotExplorer(DistributionExplorer):
    """
    BoxPlotExplorer is an explorer that returns a box plot
    of selected columns of a dataset.
    """

    DISPLAY_NAME = MultilingualString(en="Box Plot", es="Diagrama de Caja")
    DESCRIPTION = MultilingualString(
        en=(
            "Returns a box plot of selected columns in the dataset to visualize "
            "distribution and outliers."
        ),
        es=(
            "Devuelve un diagrama de caja de columnas seleccionadas del dataset "
            "para visualizar distribución y valores atípicos."
        ),
    )
    IMAGE_PREVIEW = "box_plot.png"

    SCHEMA = BoxPlotSchema
    metadata: Dict[str, Any] = {
        # It should be added, maybe in a own validate_columns method,
        # that in this case at least one column should be numeric
        "allowed_dtypes": ["int64", "float64"],
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
        import plotly.express as px

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

    def save_notebook(
        self,
        __notebook_info__: Notebook,
        explorer_info: Explorer,
        save_path: pathlib.Path,
        result: Any,
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
        from plotly.io import read_json

        result = read_json(exploration_path)
        result = result.to_json()

        return {"data": result, "type": resultType, "config": config}
