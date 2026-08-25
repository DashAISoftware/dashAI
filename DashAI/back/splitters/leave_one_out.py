from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import LeaveOneOut

from DashAI.back.core.schema_fields import BaseSchema, float_field, schema_field
from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class LeaveOneOutSplitterSchema(BaseSchema):
    """Schema that configures the Leave-One-Out splitter.

    Leave-One-Out creates one fold per sample, using it as the test set while
    every other sample is used for training. The number of folds is always the
    dataset size and ``sklearn.model_selection.LeaveOneOut`` is deterministic,
    so it accepts neither ``n_splits``, ``shuffle`` nor ``random_state``. Only
    the data held out for explanations is configurable.
    """

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


class LeaveOneOutSplitter(FoldSplitter):
    """Splitter that creates one fold per sample by leaving one example out at a time.

    This exhaustive strategy is useful for very small datasets where every
    observation should be tested in turn and the computational cost remains
    acceptable. It is often used as a reference method in small-sample studies
    and in settings where a highly thorough estimate of performance is desired.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.LeaveOneOut.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
        "TranslationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Leave-One-Out",
        es="Dejar Uno Fuera",
        pt="Deixar Um Fora",
        de="Leave-One-Out",
        zh="留一法",
    )
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]
    SCHEMA = LeaveOneOutSplitterSchema

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs following the leave-one-out scheme.

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
            A list of train/test index pairs, one for each sample in the dataset.
        """
        indexes = np.arange(len(x))

        try:
            loo = LeaveOneOut()
            folds = list(loo.split(indexes))
        except ValueError as e:
            raise ValueError(f"Error in LeaveOneOut splitting: {e}") from e

        return folds
