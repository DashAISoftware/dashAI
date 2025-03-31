import os
import pathlib

import numpy as np
import pandas as pd
from beartype.typing import Any, Dict

from DashAI.back.core.schema_fields import (
    enum_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Exploration, Explorer
from DashAI.back.exploration.base_explorer import BaseExplorer, BaseExplorerSchema


class DescribeExplorerSchema(BaseExplorerSchema):
    percentiles: schema_field(
        none_type(string_field()),
        "25, 50, 75",
        (
            "The percentiles to include in the exploration. "
            "Must be a list of integers between 0 and 100.\n"
            "Example: '25, 50, 75'"
        ),
    )  # type: ignore
    include: schema_field(
        none_type(enum_field(["all", "number", "object", "category", "datetime"])),
        "all",
        ("The data types to include in the exploration.\n"),
    )  # type: ignore
    exclude: schema_field(
        none_type(enum_field(["object", "number", "category", "datetime"])),
        None,
        ("The data types to exclude in the exploration."),
    )  # type: ignore


class DescribeExplorer(BaseExplorer):
    """
    DescribeExplorer is an explorer that uses the pandas describe method to
    describe the dataset. It returns a tabular representation of the dataset
    with the count, mean, std, min, 25%, 50%, 75%, and max values for numeric
    columns and count, unique, top, and freq values for object columns.

    The user can specify the percentiles to include in the exploration and the
    data types to include or exclude.
    """

    DISPLAY_NAME = "Describe Dataset"
    DESCRIPTION = (
        "DescribeExplorer is an explorer that describes the dataset. It returns"
        " a tabular representation of the dataset with the count, mean, std, min,"
        " 25%, 50%, 75%, and max values for numeric columns and count, unique,"
        " top, and freq values for object columns."
        "\n"
        "The user can specify the percentiles to include in the exploration and"
        " the data types to include or exclude."
    )

    SCHEMA = DescribeExplorerSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 1},
    }

    def __init__(self, **kwargs) -> None:
        # transform percentiles to list of floats for describe (e.g., [0.25, 0.5, 0.75])
        if kwargs.get("percentiles"):
            percentiles = kwargs["percentiles"].strip().split(",")
            percentiles = [percentile.strip() for percentile in percentiles]

            if percentiles == [""]:
                percentiles = None
            else:
                percentiles = [float(percentile) / 100 for percentile in percentiles]
            kwargs["percentiles"] = percentiles

        if kwargs.get("include") and kwargs["include"] != "all":
            kwargs["include"] = [kwargs["include"]]

        if kwargs.get("exclude"):
            kwargs["exclude"] = [kwargs["exclude"]]

        self.percentiles = kwargs["percentiles"]
        self.include = kwargs["include"]
        self.exclude = kwargs["exclude"]
        super().__init__(**kwargs)

    @classmethod
    def validate_parameters(cls, params: Dict[str, Any]) -> bool:
        # Validate schema
        cls.SCHEMA.model_validate(params)

        # Validate percentiles (must be int between 0 and 100)
        if params.get("percentiles"):
            percentiles = params["percentiles"].strip().split(",")
            for percentile in percentiles:
                try:
                    int_percentile = int(percentile)
                    if not 0 <= int_percentile <= 100:
                        return False
                except ValueError:
                    return False
        return True

    def launch_exploration(
        self, dataset: DashAIDataset, __explorer_info__: Explorer
    ) -> pd.DataFrame:
        return dataset.to_pandas().describe(
            percentiles=self.percentiles, include=self.include, exclude=self.exclude
        )

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
        result = (
            pd.read_json(path).replace({np.nan: None}).T.to_dict(orient=orientation)
        )
        return {"type": resultType, "data": result, "config": config}
