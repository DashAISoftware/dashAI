import os
import pathlib

import numpy as np
import pandas as pd
from beartype.typing import Any, Dict

from DashAI.back.core.schema_fields import bool_field, int_field, schema_field
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Exploration, Explorer
from DashAI.back.exploration.base_explorer import BaseExplorer, BaseExplorerSchema


class RowExplorerSchema(BaseExplorerSchema):
    row_ammount: schema_field(
        t=int_field(gt=0),
        placeholder=50,
        description="The maximum number of rows to take.",
    )  # type: ignore
    shuffle: schema_field(
        t=bool_field(),
        placeholder=False,
        description="Shuffle the rows at exploration time.",
    )  # type: ignore
    from_top: schema_field(
        t=bool_field(),
        placeholder=True,
        description=(
            "Take the rows from the Head of the dataset. " "Else, take from the Tail."
        ),
    )  # type: ignore


class RowExplorer(BaseExplorer):
    """
    RowExplorer is an explorer that takes a number of rows from the dataset to
    display them on tabular format. It can take the rows from the top or the
    bottom of the dataset and shuffle them if needed.
    """

    DISPLAY_NAME = "Show Rows"
    DESCRIPTION = (
        "RowExplorer is an explorer that takes a number of rows from the dataset to "
        "display them on tabular format. It can take the rows from the top or the "
        "bottom of the dataset and shuffle them if needed."
    )

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

    def save_exploration(
        self,
        __exploration_info__: Exploration,
        explorer_info: Explorer,
        save_path: pathlib.Path,
        result: pd.DataFrame,
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
        result = pd.read_json(path).replace({np.nan: None}).to_dict(orient=orientation)
        return {"type": resultType, "data": result, "config": config}
