from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import StratifiedKFold

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter, sklearn_random_state

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
            en=(
                "Whether to shuffle the data before splitting it into folds. When "
                "shuffling is disabled, the random state has no effect."
            ),
            es=(
                "Si se deben mezclar los datos antes de dividirlos en particiones. "
                "Cuando la mezcla está desactivada, el estado aleatorio no tiene "
                "efecto."
            ),
            pt=(
                "Se os dados devem ser embaralhados antes de dividi-los em partições. "
                "Quando o embaralhamento está desativado, o estado aleatório não tem "
                "efeito."
            ),
            de=(
                "Ob die Daten vor der Aufteilung in Folds gemischt werden sollen. "
                "Wenn das Mischen deaktiviert ist, hat der Zufallszustand keine "
                "Wirkung."
            ),
            zh="划分为折之前是否打乱数据。关闭打乱时，随机状态不起作用。",
        ),
        alias=MultilingualString(
            en="Shuffle", es="Mezclar", pt="Embaralhar", de="Mischen", zh="打乱"
        ),
    )  # type: ignore
    random_state: schema_field(
        int_field(ge=0),
        placeholder=42,
        description=MultilingualString(
            en=(
                "Seed used to make the split reproducible when shuffle is enabled. It "
                "is ignored when shuffling is disabled."
            ),
            es=(
                "Semilla utilizada para que la división sea reproducible cuando se "
                "activa la mezcla. Se ignora cuando la mezcla está desactivada."
            ),
            pt=(
                "Semente usada para tornar a divisão reproduzível quando o "
                "embaralhamento está ativado. É ignorada quando o embaralhamento está "
                "desativado."
            ),
            de=(
                "Seed, um die Aufteilung reproduzierbar zu machen, wenn Mischen "
                "aktiviert ist. Wird ignoriert, wenn das Mischen deaktiviert ist."
            ),
            zh="启用打乱时，用于使划分可复现的随机种子。关闭打乱时将被忽略。",
        ),
        alias=MultilingualString(
            en="Random state",
            es="Estado aleatorio",
            pt="Estado aleatório",
            de="Zufallszustand",
            zh="随机状态",
        ),
    )  # type: ignore
    holdout: schema_field(
        float_field(ge=0, le=0.5),
        placeholder=0.1,
        description=MultilingualString(
            en=(
                "Proportion of the dataset kept out of cross-validation. Those rows "
                "are never used to fit or select the model, so they are the data the "
                "final model can be explained on. Set it to 0 to cross-validate every "
                "row, which leaves the run without data to explain."
            ),
            es=(
                "Proporción del dataset que se mantiene fuera de la validación "
                "cruzada. Esas filas nunca se usan para ajustar ni seleccionar el "
                "modelo, por lo que son los datos con los que se puede explicar el "
                "modelo final. Usa 0 para validar de forma cruzada todas las filas, "
                "lo que deja la ejecución sin datos que explicar."
            ),
            pt=(
                "Proporção do dataset mantida fora da validação cruzada. Essas linhas "
                "nunca são usadas para ajustar ou selecionar o modelo, portanto são "
                "os dados com os quais o modelo final pode ser explicado. Use 0 para "
                "validar de forma cruzada todas as linhas, o que deixa a execução sem "
                "dados para explicar."
            ),
            de=(
                "Anteil des Datensatzes, der von der Kreuzvalidierung ausgenommen "
                "wird. Diese Zeilen werden nie zum Trainieren oder Auswählen des "
                "Modells verwendet und sind daher die Daten, mit denen das endgültige "
                "Modell erklärt werden kann. Mit 0 werden alle Zeilen "
                "kreuzvalidiert, wodurch der Lauf keine Daten zum Erklären hat."
            ),
            zh=(
                "从交叉验证中保留的数据集比例。这些行不会用于拟合或选择模型，"
                "因此可用于解释最终模型。设为 0 时全部行都参与交叉验证，"
                "该运行将没有可解释的数据。"
            ),
        ),
        alias=MultilingualString(
            en="Held out for explanations",
            es="Reservado para explicaciones",
            pt="Reservado para explicações",
            de="Für Erklärungen zurückgehalten",
            zh="用于解释的保留数据",
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

    HOLDOUT_STRATEGY: str = "stratified"
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
                random_state=sklearn_random_state(self.shuffle, self.random_state),
            )
            folds = list(kf.split(indexes, y=y_labels))
        except ValueError as e:
            raise ValueError(f"Error in StratifiedKFold splitting: {e}") from e

        return folds
