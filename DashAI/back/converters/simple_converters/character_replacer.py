from typing import List, Union

from datasets import Value

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.schema_fields import none_type, schema_field, string_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class CharacterReplacerSchema(BaseSchema):
    char_to_replace: schema_field(
        string_field(),
        "",  # default: empty string
        description="The character or substring to be replaced. Cannot be empty.",
    )  # type: ignore
    replacement_char: schema_field(
        none_type(string_field()),
        None,
        description=(
            "The character or substring to replace with. "
            "If null, 'char_to_replace' will be removed."
        ),
    )  # type: ignore


class CharacterReplacer(BaseConverter):
    """
    Converter that replaces specified characters or substrings in string columns.
    If 'replacement_char' is an empty string, 'char_to_replace' will be removed.
    """

    SCHEMA = CharacterReplacerSchema
    DESCRIPTION = (
        "Replaces or removes specified characters/substrings "
        "in selected string columns."
    )

    def __init__(self, char_to_replace: str, replacement_char: str):
        super().__init__()
        if not isinstance(char_to_replace, str) or not char_to_replace:
            raise ValueError("'char_to_replace' must be a non-empty string.")

        self.char_to_replace = char_to_replace
        if replacement_char is None or not isinstance(replacement_char, str):
            replacement_char = ""
        self.replacement_char = replacement_char
        self._target_columns: List[str] = []

    def fit(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> "CharacterReplacer":
        """
        Validates that the scoped columns (provided in x) are of string type.
        """
        self._target_columns = []
        if not x.column_names:
            return self

        for col_name in x.column_names:
            if col_name in x.features and x.features[col_name] == Value(
                dtype="string", id=None
            ):
                self._target_columns.append(col_name)
            else:
                print(
                    f"Warning: Column '{col_name}' in scope is not of string type "
                    "and will be ignored by CharacterReplacer."
                )
        if not self._target_columns:
            print(
                "Warning: CharacterReplacer did not find any valid string columns "
                "in the provided scope."
            )
        return self

    def transform(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> DashAIDataset:
        """
        Replaces or removes characters in the target string columns of the dataset x.
        If all values in a column become numeric after replacement, converts to int.
        """
        if not self._target_columns:
            # if no target columns were set, return the dataset unchanged
            return x

        def try_convert_to_int(value):
            """Try to convert a value to integer, return original if not possible."""
            try:
                return int(value)
            except (ValueError, TypeError):
                return value

        def replace_function(batch):
            processed_batch = {}
            for column_name, values in batch.items():
                if column_name in self._target_columns:
                    if x.features[column_name] == Value(dtype="string", id=None):
                        replaced_values = [
                            (
                                val.replace(self.char_to_replace, self.replacement_char)
                                if isinstance(val, str)
                                else val
                            )
                            for val in values
                        ]

                        all_numeric = all(
                            isinstance(val, str) and val.strip().isdigit()
                            for val in replaced_values
                            if isinstance(val, str)
                        )

                        if all_numeric:
                            processed_batch[column_name] = [
                                try_convert_to_int(val) for val in replaced_values
                            ]
                        else:
                            processed_batch[column_name] = replaced_values
                    else:
                        processed_batch[column_name] = values
                else:
                    processed_batch[column_name] = values
            return processed_batch

        transformed_hf_dataset = x.map(replace_function, batched=True)

        return DashAIDataset(
            transformed_hf_dataset.data.table,
            splits=x.splits,
        )

    def changes_row_count(self) -> bool:
        """This converter does not change the number of rows."""
        return False
