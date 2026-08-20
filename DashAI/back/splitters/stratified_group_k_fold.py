from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    int_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter, sklearn_random_state

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class StratifiedGroupKFoldSplitterSchema(BaseSchema):
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
    group_column: schema_field(
        none_type(string_field()),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Name of the dataset column that identifies the group each "
                "sample belongs to. Samples that share the same group are "
                "always kept together in the same fold."
            ),
            es=(
                "Nombre de la columna del dataset que identifica el grupo al "
                "que pertenece cada muestra. Las muestras que comparten grupo "
                "siempre se mantienen juntas en la misma partición."
            ),
            pt=(
                "Nome da coluna do dataset que identifica o grupo ao qual "
                "cada amostra pertence. Amostras que compartilham o mesmo "
                "grupo permanecem sempre juntas na mesma partição."
            ),
            de=(
                "Name der Datensatzspalte, die die Gruppe jeder Probe "
                "identifiziert. Proben derselben Gruppe bleiben immer im "
                "selben Fold."
            ),
            zh="标识每个样本所属分组的数据集列名。同一分组的样本始终保持在同一折中。",
        ),
        alias=MultilingualString(
            en="Group column",
            es="Columna de grupo",
            pt="Coluna de grupo",
            de="Gruppenspalte",
            zh="分组列",
        ),
    )  # type: ignore
    shuffle: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Whether to shuffle each group's samples before splitting.",
            es="Si se deben mezclar las muestras de cada grupo antes de dividir.",
            pt="Se as amostras de cada grupo devem ser embaralhadas antes de dividir.",
            de="Ob die Proben jeder Gruppe vor der Aufteilung gemischt werden sollen.",
            zh="划分前是否打乱每个分组内的样本。",
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


class StratifiedGroupKFoldSplitter(FoldSplitter):
    """Splitter that preserves both class balance and group membership in each fold.

    This strategy is particularly valuable for grouped classification tasks where
    the target labels are imbalanced and the samples are also organized into
    non-independent groups. It simultaneously prevents leakage across groups and
    keeps the class distribution similar across folds, which makes the
    evaluation more reliable and less biased.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Stratified Group K-Fold",
        es="K-Fold Estratificado por Grupos",
        pt="K-Fold Estratificado por Grupos",
        de="Stratifiziertes Gruppen-K-Fold",
        zh="分层分组 K 折交叉验证",
    )
    COMPATIBLE_INNER_SPLITTERS = ["GroupKFoldSplitter", "StratifiedGroupKFoldSplitter"]
    SCHEMA = StratifiedGroupKFoldSplitterSchema

    def __init__(self, splits_data):
        """Initialize the stratified group-based K-fold splitter.

        Parameters
        ----------
        splits_data : dict
            Configuration dictionary that may include the name of the group
            column used to define the groups.
        """
        super().__init__(splits_data)
        self.group_column = splits_data.get("group_column", None)

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs preserving both labels and groups.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset that can be converted to a pandas DataFrame.
        y : DashAIDataset
            Target values used to preserve class balance across folds.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs preserving group and label balance.
        """
        indexes = np.arange(len(x))

        try:
            try:
                dataset_df = x.to_pandas()
            except Exception as e:
                raise ValueError(
                    f"""Input x must be convertible
                    to a pandas DataFrame for StratifiedGroupKFold splitting: {e}"""
                ) from e

            try:
                y_labels = self.prepare_y(y)
            except Exception as e:
                raise ValueError(
                    f"""y must be convertible to a format suitable for
                    StratifiedGroupKFold splitting: {e}"""
                ) from e

            dataset_df_groups = dataset_df[self.group_column]

            sgkf = StratifiedGroupKFold(
                n_splits=self.n_splits,
                shuffle=self.shuffle,
                random_state=sklearn_random_state(self.shuffle, self.random_state),
            )
            folds = list(sgkf.split(indexes, y=y_labels, groups=dataset_df_groups))
        except ValueError as e:
            raise ValueError(f"Error in StratifiedGroupKFold splitting: {e}") from e

        return folds
