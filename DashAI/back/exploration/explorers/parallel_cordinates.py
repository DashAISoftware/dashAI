from typing import TYPE_CHECKING, Any, Dict, List, Union

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
from DashAI.back.exploration.multidimensional_explorer import MultidimensionalExplorer

if TYPE_CHECKING:
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ParallelCordinatesSchema(BaseExplorerSchema):
    color_column: schema_field(
        none_type(union_type(string_field(), int_field(ge=0))),
        None,
        description=MultilingualString(
            en=("Column used to color the data points."),
            es=("Columna usada para colorear los puntos."),
        ),
        alias=MultilingualString(en="Color column", es="Columna de color"),
    )  # type: ignore


class ParallelCordinatesExplorer(MultidimensionalExplorer):
    """
    Parallel Cordinates Explorer is a class that generates a parallel cordinates plot
    for a given dataset.
    """

    DISPLAY_NAME = MultilingualString(
        en="Parallel Coordinates Plot",
        es="Gráfico de Coordenadas Paralelas",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Common way to visualize high-dimensional numeric data. Each line is "
            "a data point crossing axes for each feature."
        ),
        es=(
            "Forma común de visualizar datos numéricos de alta dimensión. Cada "
            "línea es un dato que cruza ejes para cada característica."
        ),
    )
    IMAGE_PREVIEW = "parallel_cordinates.png"

    SCHEMA = ParallelCordinatesSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["float64", "float32", "int64"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 2},
    }

    def __init__(self, **kwargs) -> None:
        """Initialize the ParallelCordinatesExplorer with an optional color column.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments. Recognized keys:
            color_column (str or int, optional): Column name or index used
            to color each line. Defaults to None.
        """
        self.color_column: Union[str, int, None] = kwargs.get("color_column")
        super().__init__(**kwargs)

    def prepare_dataset(
        self, loaded_dataset: "DashAIDataset", columns: List[Dict[str, Any]]
    ) -> "DashAIDataset":
        """Extend column selection to include the optional color column.

        Parameters
        ----------
        loaded_dataset : DashAIDataset
            The full dataset.
        columns : List[Dict[str, Any]]
            Explicitly selected column descriptors.

        Returns
        -------
        DashAIDataset
            Dataset containing the selected columns plus the
            optional color column.
        """
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

        return super().prepare_dataset(loaded_dataset, columns)

    def launch_exploration(self, dataset: "DashAIDataset", explorer_info: Explorer):
        """Generate a Plotly parallel coordinates plot for the selected columns.

        Each line in the plot represents one data row, crossing a vertical axis
        for each selected feature. Useful for visualizing patterns across many
        numeric dimensions simultaneously.

        Parameters
        ----------
        dataset : DashAIDataset
            The prepared dataset with at least two columns.
        explorer_info : Explorer
            Explorer record with column names and optional
            display name.

        Returns
        -------
        plotly.graph_objects.Figure
            An interactive parallel coordinates figure.
        """
        import plotly.express as px

        _df = dataset.to_pandas()
        columns = [col["columnName"] for col in explorer_info.columns]

        fig = px.parallel_coordinates(
            _df,
            dimensions=columns,
            color=self.color_column,
            title=(f"Parallel Cordinates Plot of {len(columns)} columns"),
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
        """Save the parallel coordinates figure to a JSON file on disk.

        Parameters
        ----------
        __notebook_info__ : Notebook
            The notebook database record (unused).
        explorer_info : Explorer
            The explorer record used for filename generation.
        save_path : Path
            Directory where the file will be saved.
        result : Any
            The Plotly figure returned by `launch_exploration`.

        Returns
        -------
        str
            The path of the saved JSON file as a POSIX string.
        """
        import os
        from pathlib import Path

        filename = f"{explorer_info.id}.json"
        path = Path(os.path.join(save_path, filename))

        result.write_json(path.as_posix())
        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Load and return the saved parallel coordinates plot for the frontend.

        Parameters
        ----------
        exploration_path : str
            Path to the JSON file saved by `save_notebook`.
        options : Dict[str, Any]
            Rendering options from the frontend (unused).

        Returns
        -------
        Dict[str, Any]
            Dictionary with keys ``"data"`` (JSON-serialized
            Plotly figure), ``"type"`` (``"plotly_json"``), and
            ``"config"`` (empty dict).
        """
        import plotly.io as pio

        resultType = "plotly_json"
        config = {}

        result = pio.read_json(exploration_path)
        result = result.to_json()

        return {"data": result, "type": resultType, "config": config}
