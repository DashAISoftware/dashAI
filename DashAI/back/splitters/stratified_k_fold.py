from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import StratifiedKFold

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class StratifiedKFoldSplitterSchema(BaseSchema):
    n_splits: schema_field(
        int_field(ge=2, le=20),
        placeholder=5,
        description=MultilingualString(
            en="Number of folds. Must be an integer between 2 and 20.",
            es="Número de particiones. Debe ser un entero entre 2 y 20.",
            pt="Número de partições. Deve ser um inteiro entre 2 e 20.",
            de="Anzahl der Folds. Muss eine ganze Zahl zwischen 2 und 20 sein.",
            zh="折数，必须为2到20之间的整数。",
        ),
        alias=MultilingualString(
            en="Number of folds",
            es="Número de particiones",
            pt="Número de partições",
            de="Anzahl der Folds",
            zh="折数",
        ),
    )  # type: ignore
    shuffle: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Whether to shuffle the data before splitting it into folds.",
            es="Si se deben mezclar los datos antes de dividirlos en particiones.",
            pt="Se os dados devem ser embaralhados antes de dividi-los em partições.",
            de="Ob die Daten vor der Aufteilung in Folds gemischt werden sollen.",
            zh="划分为折之前是否打乱数据。",
        ),
        alias=MultilingualString(
            en="Shuffle", es="Mezclar", pt="Embaralhar", de="Mischen", zh="打乱"
        ),
    )  # type: ignore
    random_state: schema_field(
        int_field(ge=0),
        placeholder=42,
        description=MultilingualString(
            en="Seed used to make the split reproducible when shuffle is enabled.",
            es=(
                "Semilla utilizada para que la división sea reproducible cuando "
                "se activa la mezcla."
            ),
            pt=(
                "Semente usada para tornar a divisão reproduzível quando o "
                "embaralhamento está ativado."
            ),
            de=(
                "Seed, um die Aufteilung reproduzierbar zu machen, wenn Mischen "
                "aktiviert ist."
            ),
            zh="启用打乱时，用于使划分可复现的随机种子。",
        ),
        alias=MultilingualString(
            en="Random state",
            es="Estado aleatorio",
            pt="Estado aleatório",
            de="Zufallszustand",
            zh="随机状态",
        ),
    )  # type: ignore


class StratifiedKFoldSplitter(FoldSplitter):
    """Splitter that generates folds while preserving the class distribution.

    This strategy is particularly useful for classification problems with
    imbalanced labels, where each fold should retain a similar proportion of
    each class to produce a more meaningful and less biased estimate of model
    performance.

    It is commonly used in tabular and image classification tasks when the
    evaluation must reflect the original class distribution.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedKFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Stratified K-Fold",
        es="K-Fold Estratificado",
        pt="K-Fold Estratificado",
        de="Stratifiziertes K-Fold",
        zh="分层 K 折交叉验证",
    )
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]
    SCHEMA = StratifiedKFoldSplitterSchema

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs while preserving class proportions.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset whose length determines the number of available samples.
        y : DashAIDataset
            Target values used to preserve the class distribution across folds.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs for every stratified fold.
        """
        indexes = np.arange(len(x))

        try:
            y_labels = self.prepare_y(y)

            kf = StratifiedKFold(
                n_splits=self.n_splits,
                shuffle=self.shuffle,
                random_state=self.random_state,
            )
            folds = list(kf.split(indexes, y=y_labels))
        except ValueError as e:
            raise ValueError(f"Error in StratifiedKFold splitting: {e}") from e

        return folds
