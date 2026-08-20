from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import KFold

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


class KFoldSplitterSchema(BaseSchema):
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


class KFoldSplitter(FoldSplitter):
    """Splitter that generates K folds for cross-validation.

    This strategy is a standard choice for estimating model performance when the
    data is not naturally grouped and the goal is to obtain several
    semi-independent evaluation partitions. It is widely used in supervised
    learning tasks such as tabular classification, regression, text processing,
    and image classification.

    It is especially useful when a reliable estimate of generalization is needed
    without the additional complexity of group-aware or stratified schemes.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
        "TranslationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="K-Fold",
        es="K-Fold",
        pt="K-Fold",
        de="K-Fold",
        zh="K 折交叉验证",
    )
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]
    SCHEMA = KFoldSplitterSchema

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs for each K-fold split.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset whose length determines the number of available samples.
        y : DashAIDataset
            Target values associated with ``x``. This argument is accepted for
            interface consistency but is not used directly by the splitter.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs for every fold.
        """
        indexes = np.arange(len(x))

        try:
            kf = KFold(
                n_splits=self.n_splits,
                shuffle=self.shuffle,
                random_state=self.random_state if self.shuffle else None,
            )
            folds = list(kf.split(indexes))
        except ValueError as e:
            raise ValueError(
                f"""Error in KFold splitting: {e}.
                Check if n_splits is less than or equal
                to the number of samples."""
            ) from e

        return folds
