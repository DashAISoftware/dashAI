import os
import pathlib

from beartype.typing import Any, Dict

from DashAI.back.core.schema_fields import bool_field, int_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.preview_inspection_explorer import (
    PreviewInspectionExplorer,
)


class RowExplorerSchema(BaseExplorerSchema):
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
    """
    RowExplorer is an explorer that takes a number of rows from the dataset to
    display them on tabular format. It can take the rows from the top or the
    bottom of the dataset and shuffle them if needed.
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
        self.row_ammount = kwargs.get("row_ammount", 50)
        self.shuffle = kwargs.get("shuffle", True)
        self.from_top = kwargs.get("from_top", True)
        super().__init__(**kwargs)

    def launch_exploration(self, dataset: DashAIDataset, __explorer_info__: Explorer):
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
        save_path: pathlib.Path,
        result: Any,
    ) -> str:
        filename = f"{explorer_info.id}.json"
        path = pathlib.Path(os.path.join(save_path, filename))

        result.to_json(path)
        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        resultType = "tabular"
        orientation = options.get("orientation", "dict")
        config = {"orient": orientation}

        path = pathlib.Path(exploration_path)
        import numpy as np
        import pandas as pd

        result = pd.read_json(path).replace({np.nan: None}).to_dict(orient=orientation)
        return {"type": resultType, "data": result, "config": config}
