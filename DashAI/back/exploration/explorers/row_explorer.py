from typing import TYPE_CHECKING, Any, Dict

from DashAI.back.core.schema_fields import bool_field, int_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.preview_inspection_explorer import (
    PreviewInspectionExplorer,
)

if TYPE_CHECKING:
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class RowExplorerSchema(BaseExplorerSchema):
    """Schema for RowExplorer hyperparameters.

    Configures how many rows are sampled (``row_ammount``), whether to take
    them from the head or tail of the dataset (``from_top``), and whether to
    shuffle before sampling (``shuffle``).
    """

    row_ammount: schema_field(
        t=int_field(gt=0),
        placeholder=50,
        description=MultilingualString(
            en="Maximum number of rows to take.",
            es="Número máximo de filas a tomar.",
        ),
        alias=MultilingualString(en="Number of rows", es="Número de filas"),
    )  # type: ignore
    shuffle: schema_field(
        t=bool_field(),
        placeholder=False,
        description=MultilingualString(
            en="Shuffle the rows when exploring.",
            es="Barajar las filas durante la exploración.",
        ),
        alias=MultilingualString(en="Shuffle rows", es="Barajar filas"),
    )  # type: ignore
    from_top: schema_field(
        t=bool_field(),
        placeholder=True,
        description=MultilingualString(
            en=(
                "Take rows from the head of the dataset. Otherwise, take from the tail."
            ),
            es=(
                "Tomar filas desde el inicio del dataset. En caso contrario, "
                "tomarlas desde el final."
            ),
        ),
        alias=MultilingualString(en="From top", es="Desde el inicio"),
    )  # type: ignore


class RowExplorer(PreviewInspectionExplorer):
    """Display a tabular sample of dataset rows for direct data inspection.

    Returns up to ``row_ammount`` rows from the dataset rendered as a table.
    Rows can be taken from the head or tail of the dataset, and optionally
    shuffled before sampling to obtain a random preview. This is typically the
    first exploration step after loading a dataset, allowing users to verify
    column types, spot obvious data quality issues, and understand the raw
    data format before applying transformations.
    """

    DISPLAY_NAME = MultilingualString(en="Show Rows", es="Mostrar Filas")
    DESCRIPTION = MultilingualString(
        en=(
            "Displays a subset of rows from the dataset in tabular form. You can "
            "take rows from the top or bottom and optionally shuffle them."
        ),
        es=(
            "Muestra un subconjunto de filas del dataset en formato tabular. "
            "Puede tomar filas desde el inicio o el final y opcionalmente "
            "barajarlas."
        ),
    )

    SHORT_DESCRIPTION = MultilingualString(
        en="Display a sample of rows from the dataset.",
        es="Muestra una muestra de filas del dataset.",
    )
    IMAGE_PREVIEW = "row_explorer.png"

    SCHEMA = RowExplorerSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 1},
    }

    def __init__(self, **kwargs) -> None:
        """Initialize RowExplorer with row-sampling parameters.

        Parameters
        ----------
        **kwargs
            Keyword arguments matching ``RowExplorerSchema`` fields:
            row_ammount (int): Maximum number of rows to return. Defaults
            to ``50``.
            shuffle (bool): Whether to shuffle the dataset rows before
            sampling. Defaults to ``False``.
            from_top (bool): When ``True``, take rows from the head of the
            dataset; when ``False``, take from the tail. Defaults to
            ``True``.
        """
        self.row_ammount = kwargs.get("row_ammount", 50)
        self.shuffle = kwargs.get("shuffle", True)
        self.from_top = kwargs.get("from_top", True)
        super().__init__(**kwargs)

    def launch_exploration(self, dataset: "DashAIDataset", __explorer_info__: Explorer):
        """Return a subset of dataset rows for tabular preview.

        Converts the dataset to a pandas DataFrame, optionally shuffles it,
        then takes rows from the head or tail according to the configured
        parameters.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to sample rows from.
        __explorer_info__ : Explorer
            The explorer database record (unused).

        Returns
        -------
        Any
            A ``pandas.DataFrame`` containing at most ``self.row_ammount``
            rows selected from the head or tail of the (optionally
            shuffled) dataset.
        """
        _df = dataset.to_pandas()

        # Shuffle rows
        if self.shuffle:
            _df = _df.sample(frac=1)

        # Take rows
        if self.from_top:
            _df = _df.head(self.row_ammount)
        else:
            _df = _df.tail(self.row_ammount)

        return _df

    def save_notebook(
        self,
        __notebook_info__: Notebook,
        explorer_info: Explorer,
        save_path: "Path",
        result: Any,
    ) -> str:
        """Save the sampled rows DataFrame to a JSON file on disk.

        Parameters
        ----------
        __notebook_info__ : Notebook
            The notebook database record (unused).
        explorer_info : Explorer
            The explorer record used for filename
            generation.
        save_path : Path
            Directory where the file will be saved.
        result : Any
            The ``pandas.DataFrame`` returned by
            ``launch_exploration``.

        Returns
        -------
        str
            The path of the saved JSON file as a POSIX string.
        """
        import os
        from pathlib import Path

        filename = f"{explorer_info.id}.json"
        path = Path(os.path.join(save_path, filename))

        result.to_json(path)
        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Load and return the saved row sample for the frontend.

        Reads the JSON file written by ``save_notebook`` and converts it to a
        nested dictionary for tabular display.

        Parameters
        ----------
        exploration_path : str
            Path to the JSON file saved by
            ``save_notebook``.
        options : Dict[str, Any]
            Rendering options from the frontend.
            Supports ``"orientation"`` (str, default ``"dict"``), which is
            forwarded to ``pandas.DataFrame.to_dict``.

        Returns
        -------
        Dict[str, Any]
            Dictionary with keys ``"data"`` (nested dict of
            the sampled rows in the requested orientation), ``"type"``
            (``"tabular"``), and ``"config"`` (dict containing
            ``{"orient": <orientation>}``).
        """
        from pathlib import Path

        import numpy as np
        import pandas as pd

        resultType = "tabular"
        orientation = options.get("orientation", "dict")
        config = {"orient": orientation}

        path = Path(exploration_path)

        result = pd.read_json(path).replace({np.nan: None}).to_dict(orient=orientation)
        return {"type": resultType, "data": result, "config": config}
