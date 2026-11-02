from typing import TYPE_CHECKING, Dict, Final, List, Optional, Union

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.preprocessing.structure_types import (
    ColumnItem,
    StateItem,
    StructureDelta,
    type_fields,
)
from DashAI.back.static.icons import Icon

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class EncodingConverter(BaseConverter):
    """Base class for converters that encode categorical features into numeric form.

    Encoding converters transform non-numeric columns into a representation
    that machine learning models can process. Examples include OneHotEncoder,
    OrdinalEncoder, and LabelEncoder.

    Use these converters when the dataset contains string or categorical columns
    that must be converted before model training.

    The ``transform`` method appends encoded columns (``encoded_<col>``) to the
    dataset instead of replacing the originals, so the source column is always
    preserved.
    """

    CATEGORY = MultilingualString(
        en="Encoding", es="Codificación", pt="Codificação", de="Kodierung", zh="编码"
    )
    ICON: Final[str] = Icon.Dns.value
    COLOR: Final[str] = "rgb(138, 43, 226)"
    COLUMN_OPERATION = "add"
    PREFIX: str = "encoded_"
    # Whether the converter appends exactly one PREFIX column per encoded
    # scope column (ordinal, label, binarizer). One-hot appends one column
    # per category instead, a count only known after fit.
    ONE_COLUMN_PER_INPUT: bool = False
    #: What to change so the converter treats a category it did not see in
    #: fit instead of raising, for the message of one set to raise. None for
    #: converters that always treat it.
    UNKNOWN_HINT: Optional[str] = None

    def raises_on_unseen(self) -> bool:
        """Whether a category unseen in fit makes ``transform`` raise."""
        return getattr(self, "handle_unknown", None) == "error"

    def unseen_values(self, x: "DashAIDataset") -> Dict[str, List[str]]:
        """The values of each column of ``x`` that the fit did not see.

        Read from the categories the sklearn encoder learnt, so it only
        answers for encoders that have them; the others report nothing.
        Missing values are not categories and are never reported.

        Parameters
        ----------
        x : DashAIDataset
            Rows of the converter's scope, as ``transform`` would get them.

        Returns
        -------
        dict
            Column name to its unseen values as sorted strings, only for the
            columns that have any.
        """
        categories = getattr(self, "categories_", None)
        if categories is None:
            return {}
        names = getattr(self, "feature_names_in_", x.column_names)
        frame = x.to_pandas()
        unseen = {}
        for name, known in zip(names, categories, strict=False):
            if name not in frame.columns:
                continue
            values = frame[name].dropna()
            new = sorted({str(v) for v in values[~values.isin(known)]})
            if new:
                unseen[name] = new
        return unseen

    def _encodes(self, item: ColumnItem) -> bool:
        """Whether a scope column gets an encoded copy. Defaults to all."""
        return True

    def infer_output_columns(self, inputs: List[StateItem]) -> StructureDelta:
        """Estimate the output: the scope kept, plus one encoded copy each.

        Only exact for ONE_COLUMN_PER_INPUT converters over concrete
        columns; otherwise the new columns are one block of unknown size.

        Parameters
        ----------
        inputs : list of ColumnItem | BlockItem
            The dataset state items in this converter's scope.

        Returns
        -------
        StructureDelta
            The unchanged inputs, plus the encoded columns.
        """
        concrete = all(isinstance(item, ColumnItem) for item in inputs)
        if not (type(self).ONE_COLUMN_PER_INPUT and concrete):
            return super().infer_output_columns(inputs)
        added = []
        for item in inputs:
            if not self._encodes(item):
                continue
            type_name, dtype = type_fields(self.get_output_type(item.name))
            added.append(
                ColumnItem(
                    name=f"{self.PREFIX}{item.name}", type=type_name, dtype=dtype
                )
            )
        return StructureDelta(kept=list(inputs), added=added)

    def transform(
        self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None
    ) -> "DashAIDataset":
        """Encode ``x`` and append the result as new ``encoded_*`` columns.

        Calls the underlying sklearn transformer (via ``SklearnWrapper.transform``)
        to produce encoded values, then renames every output column to
        ``encoded_<col>`` and appends them to the original dataset. The original
        scope columns are left unchanged.

        Parameters
        ----------
        x : DashAIDataset
            The dataset to transform (contains only the scope columns).
        y : DashAIDataset, optional
            Ignored. Defaults to None.

        Returns
        -------
        DashAIDataset
            Dataset with the original scope columns preserved plus new
            ``encoded_*`` columns appended.
        """
        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        encoded = super().transform(x, y)

        combined_table = x.arrow_table
        combined_types = dict(x.types)

        for col in encoded.column_names:
            prefixed = f"{self.PREFIX}{col}"
            combined_table = combined_table.append_column(
                prefixed, encoded.arrow_table[col]
            )
            combined_types[prefixed] = encoded.types[col]

        return DashAIDataset(combined_table, types=combined_types, splits=x.splits)
