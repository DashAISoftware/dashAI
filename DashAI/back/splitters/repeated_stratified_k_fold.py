from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import RepeatedStratifiedKFold

from DashAI.back.core.schema_fields import BaseSchema, int_field, schema_field
from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class RepeatedStratifiedKFoldSplitterSchema(BaseSchema):
    """Schema that configures the Repeated Stratified K-Fold splitter.

    Repeated Stratified K-Fold runs the Stratified K-Fold procedure
    ``n_repeats`` times with different randomization in each repetition,
    preserving class proportions in every fold. It does not accept a separate
    ``shuffle`` parameter, because
    ``sklearn.model_selection.RepeatedStratifiedKFold`` always reshuffles the
    data on every repetition.
    """

    n_splits: schema_field(
        int_field(ge=2),
        placeholder=5,
        description=MultilingualString(
            en="Number of folds. Must be an integer greater than or equal to 2.",
            es="Número de particiones. Debe ser un entero mayor o igual a 2.",
            pt="Número de partições. Deve ser um inteiro maior ou igual a 2.",
            de="Anzahl der Folds. Muss eine ganze Zahl größer oder gleich 2 sein.",
            zh="折数，必须为大于或等于2的整数。",
        ),
        alias=MultilingualString(
            en="Number of folds",
            es="Número de particiones",
            pt="Número de partições",
            de="Anzahl der Folds",
            zh="折数",
        ),
    )  # type: ignore
    n_repeats: schema_field(
        int_field(ge=2),
        placeholder=2,
        description=MultilingualString(
            en=(
                "Number of times the Stratified K-Fold procedure is repeated. "
                "Must be an integer greater than or equal to 2."
            ),
            es=(
                "Número de veces que se repite el procedimiento K-Fold "
                "estratificado. Debe ser un entero mayor o igual a 2."
            ),
            pt=(
                "Número de vezes que o procedimento K-Fold estratificado é "
                "repetido. Deve ser um inteiro maior ou igual a 2."
            ),
            de=(
                "Anzahl der Wiederholungen des stratifizierten K-Fold-"
                "Verfahrens. Muss eine ganze Zahl größer oder gleich 2 sein."
            ),
            zh="分层K折过程重复的次数，必须为大于或等于2的整数。",
        ),
        alias=MultilingualString(
            en="Number of repeats",
            es="Número de repeticiones",
            pt="Número de repetições",
            de="Anzahl der Wiederholungen",
            zh="重复次数",
        ),
    )  # type: ignore
    random_state: schema_field(
        int_field(ge=0),
        placeholder=42,
        description=MultilingualString(
            en="Seed used to make the repeated split reproducible.",
            es="Semilla utilizada para que la división repetida sea reproducible.",
            pt="Semente usada para tornar a divisão repetida reproduzível.",
            de="Seed, um die wiederholte Aufteilung reproduzierbar zu machen.",
            zh="用于使重复划分可复现的随机种子。",
        ),
        alias=MultilingualString(
            en="Random state",
            es="Estado aleatorio",
            pt="Estado aleatório",
            de="Zufallszustand",
            zh="随机状态",
        ),
    )  # type: ignore


class RepeatedStratifiedKFoldSplitter(FoldSplitter):
    """Splitter that repeats the stratified K-fold procedure multiple times.

    This strategy preserves class proportions in each fold while repeating the
    partitioning scheme several times, which makes it particularly useful for
    imbalanced classification problems where a stable and representative estimate
    is needed.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.RepeatedStratifiedKFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Repeated Stratified K-Fold",
        es="K-Fold Estratificado Repetido",
        pt="K-Fold Estratificado Repetido",
        de="Wiederholtes stratifiziertes K-Fold",
        zh="重复分层 K 折交叉验证",
    )
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]
    SCHEMA = RepeatedStratifiedKFoldSplitterSchema

    def __init__(self, splits_data):
        """Initialize the repeated stratified K-fold splitter.

        Parameters
        ----------
        splits_data : dict
            Configuration dictionary that may include the number of repeats.
        """
        super().__init__(splits_data)
        self.n_repeats = splits_data.get("n_repeats", 2)

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs preserving class proportions.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset whose length determines the number of available samples.
        y : DashAIDataset
            Target values used to preserve class distribution across folds.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs for all folds and repeats.
        """
        indexes = np.arange(len(x))

        try:
            y_labels = self.prepare_y(y)

            rskf = RepeatedStratifiedKFold(
                n_splits=self.n_splits,
                n_repeats=self.n_repeats,
                random_state=self.random_state,
            )
            folds = list(rskf.split(indexes, y=y_labels))
        except ValueError as e:
            raise ValueError(f"Error in RepeatedStratifiedKFold splitting: {e}") from e

        return folds
