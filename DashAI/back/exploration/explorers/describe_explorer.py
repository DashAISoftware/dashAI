import os
import pathlib

from beartype.typing import Any, Dict

from DashAI.back.core.schema_fields import (
    enum_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.preview_inspection_explorer import (
    PreviewInspectionExplorer,
)


class DescribeExplorerSchema(BaseExplorerSchema):
    percentiles: schema_field(
        none_type(string_field()),
        "25, 50, 75",
        description=MultilingualString(
            en=(
                "Percentiles to include in the exploration. Use integers between "
                "0 and 100. Example: '25, 50, 75'"
            ),
            es=(
                "Percentiles a incluir en la exploración. Use enteros entre 0 y "
                "100. Ejemplo: '25, 50, 75'"
            ),
        ),
        alias=MultilingualString(en="Percentiles", es="Percentiles"),
    )  # type: ignore
    include: schema_field(
        none_type(enum_field(["all", "number", "object", "category", "datetime"])),
        "all",
        description=MultilingualString(
            en=("Data types to include in the exploration."),
            es=("Tipos de datos a incluir en la exploración."),
        ),
        alias=MultilingualString(en="Include dtypes", es="Incluir tipos"),
    )  # type: ignore
    exclude: schema_field(
        none_type(enum_field(["object", "number", "category", "datetime"])),
        None,
        description=MultilingualString(
            en=("Data types to exclude from the exploration."),
            es=("Tipos de datos a excluir de la exploración."),
        ),
        alias=MultilingualString(en="Exclude dtypes", es="Excluir tipos"),
    )  # type: ignore


class DescribeExplorer(PreviewInspectionExplorer):
    """
    DescribeExplorer is an explorer that uses the pandas describe method to
    describe the dataset. It returns a tabular representation of the dataset
    with the count, mean, std, min, 25%, 50%, 75%, and max values for numeric
    columns and count, unique, top, and freq values for object columns.

    The user can specify the percentiles to include in the exploration and the
    data types to include or exclude.
    """

    DISPLAY_NAME = MultilingualString(
        en="Describe Dataset",
        es="Describir Dataset",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Generates a statistical summary of the dataset. For numeric "
            "columns: count, mean, std, min, 25%, 50%, 75%, and max. For "
            "object columns: count, unique, top, and freq. You can choose "
            "percentiles and which dtypes to include or exclude."
        ),
        es=(
            "Genera un resumen estadístico del dataset. Para columnas "
            "numéricas: count, mean, std, min, 25%, 50%, 75% y max. Para "
            "columnas de tipo objeto: count, unique, top y freq. Puede elegir "
            "percentiles y qué tipos incluir o excluir."
        ),
    )

    SHORT_DESCRIPTION = MultilingualString(
        en="Generate a statistical summary of the dataset.",
        es="Genera un resumen estadístico del dataset.",
    )
    IMAGE_PREVIEW = "describe_explorer.png"

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
    ) -> Any:
        return dataset.to_pandas().describe(
            percentiles=self.percentiles, include=self.include, exclude=self.exclude
        )

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

        result = (
            pd.read_json(path).replace({np.nan: None}).T.to_dict(orient=orientation)
        )
        return {"type": resultType, "data": result, "config": config}
