from typing import TYPE_CHECKING, Any, Dict

from DashAI.back.core.schema_fields import bool_field, int_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.statistical_explorer import StatisticalExplorer

if TYPE_CHECKING:
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class CovarianceMatrixExplorerSchema(BaseExplorerSchema):
    min_periods: schema_field(
        int_field(gt=0),
        1,
        description=MultilingualString(
            en=(
                "Minimum observations required per column pair to have a valid result."
            ),
            es=(
                "Número mínimo de observaciones requeridas por par de columnas "
                "para obtener un resultado válido."
            ),
        ),
        alias=MultilingualString(en="Minimum periods", es="Períodos mínimos"),
    )  # type: ignore
    delta_degree_of_freedom: schema_field(
        int_field(gt=0),
        1,
        description=MultilingualString(
            en=(
                "Delta degrees of freedom to use when calculating the covariance "
                "matrix. Only used if numeric_only is True."
            ),
            es=(
                "Grados de libertad delta a usar al calcular la matriz de "
                "covarianza. Solo se usa si numeric_only es True."
            ),
        ),
        alias=MultilingualString(
            en="Delta degrees of freedom",
            es="Grados de libertad delta",
        ),
    )  # type: ignore
    numeric_only: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=(
                "If True, include only numeric columns in the calculation; "
                "otherwise include all columns."
            ),
            es=(
                "Si es True, incluye solo columnas numéricas en el cálculo; de "
                "lo contrario incluye todas las columnas."
            ),
        ),
        alias=MultilingualString(en="Numeric only", es="Solo numéricas"),
    )  # type: ignore
    plot: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=("If True, the result will be plotted."),
            es=("Si es True, el resultado será graficado."),
        ),
        alias=MultilingualString(en="Plot result", es="Graficar resultado"),
    )  # type: ignore


class CovarianceMatrixExplorer(StatisticalExplorer):
    """
    CovarianceExplorer is an explorer that returns the covariance matrix of the dataset.

    Its result is a heatmap by default, but can also be returned as a tabular result.
    """

    DISPLAY_NAME = MultilingualString(
        en="Covariance Matrix",
        es="Matriz de Covarianza",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Returns the covariance matrix of the dataset. The default output is "
            "a heatmap, but a tabular result can also be returned."
        ),
        es=(
            "Devuelve la matriz de covarianza del dataset. Por defecto se "
            "muestra como mapa de calor, pero también puede retornarse en "
            "formato tabular."
        ),
    )
    IMAGE_PREVIEW = "covariance_matrix.png"

    SCHEMA = CovarianceMatrixExplorerSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["*"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 2},
    }

    def __init__(self, **kwargs) -> None:
        self.ddof = kwargs.get("delta_degree_of_freedom")
        self.min_periods = kwargs.get("min_periods")
        self.numeric_only = kwargs.get("numeric_only")
        self.plot = kwargs.get("plot")
        super().__init__(**kwargs)

    def launch_exploration(
        self, dataset: "DashAIDataset", explorer_info: Explorer
    ) -> Any:
        import plotly.express as px

        result = dataset.to_pandas().cov(
            min_periods=self.min_periods,
            ddof=self.ddof,
            numeric_only=self.numeric_only,
        )

        if self.plot:
            result = px.imshow(
                result,
                text_auto=True,
                aspect="auto",
                title=f"Covariance Matrix of {len(explorer_info.columns)} columns",
            )
            if explorer_info.name is not None and explorer_info.name != "":
                result.update_layout(title=f"{explorer_info.name}")

        return result

    def save_notebook(
        self,
        __notebook_info__: Notebook,
        explorer_info: Explorer,
        save_path: "Path",
        result: Any,
    ) -> str:
        import os
        from pathlib import Path

        import pandas as pd
        import plotly.graph_objects as go

        filename = f"{explorer_info.id}.json"
        path = Path(os.path.join(save_path, filename))

        if self.plot:
            assert isinstance(result, go.Figure)
            result.write_json(path)
        else:
            assert isinstance(result, pd.DataFrame)
            result.to_json(path)
        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        from pathlib import Path

        import numpy as np
        import pandas as pd

        if self.plot:
            resultType = "plotly_json"
            with open(exploration_path, "r", encoding="utf-8") as f:
                result = f.read()
            return {"type": resultType, "data": result, "config": {}}

        resultType = "tabular"
        config = {"orient": "dict"}

        path = Path(exploration_path)

        result = pd.read_json(path).replace({np.nan: None}).T.to_dict(orient="dict")
        return {"type": resultType, "data": result, "config": config}
