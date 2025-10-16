from typing import Dict, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset, modify_table
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.utils import to_arrow_types
from DashAI.back.types.value_types import Text

###### Data Transformations ######

# Categorical Transformations


def categorical_label_encoder(
    dataset: DashAIDataset,
) -> Tuple[DashAIDataset, Dict[str, Dict[str, int]]]:
    """Convert categorical columns from the DashAIDataset to label encoded integers.

    Parameters
    ----------
    dataset : DashAIDataset
        The dataset containing both non categorical
        and categorical columns to be label encoded.

    Returns
    -------
    DashAIDataset
        A new DashAIDataset with categorical columns converted to
        label encoded integers.
    encodings : dict
        A dictionary containing the encodings for each categorical column,
        where keys are column names and values.
    """
    new_columns = {}
    table = dataset.arrow_table
    encodings = {}

    for col, _type in dataset.types.items():
        array = table[col]
        # Check every column dashai_type to find the categorical ones
        if isinstance(_type, Categorical):
            encodings[col] = dict(_type._str2int)  # Store the encoding for later use

            # Need to check everything later, predictions and model reuse.
            if not _type.converted:
                values = [_type.str2int(x.as_py()) for x in array]
                new_columns[col] = pa.array(values, type=pa.int64())
            else:
                new_columns[col] = array
        else:
            new_columns[col] = array

    return modify_table(dataset, columns=new_columns, types=dataset.types), encodings


# This function is used to apply the encodings stored in the model
# to the categorical columns in the dataset.
def apply_categorical_label_encoder(
    dataset: DashAIDataset, encodings: Dict[str, Dict[str, int]]
) -> DashAIDataset:
    """Apply Model stored encodings to the categorical columns in the dataset.

    Parameters
    ----------
    dataset : DashAIDataset
        The dataset containing both non categorical and categorical columns
        to be label encoded.
    encodings : dict
        A dictionary containing the encodings for each categorical column,
        where keys are column names and values are dictionaries
        mapping original values to encoded integers.

    Returns
    -------
    DashAIDataset
        A new DashAIDataset with categorical columns converted to
        label encoded integers using the provided encodings.

    """

    table = dataset.arrow_table
    new_columns = {}
    types = dataset.types

    for col in table.column_names:
        array = table[col]
        _type = types[col]

        if col in encodings and isinstance(_type, Categorical) and not _type.converted:
            # Apply the stored encodings to the categorical columns

            encoding = encodings[col]
            try:
                categories = _type.categories
                cat_type = Categorical(categories, encoding=encoding)
                encoded_values = [cat_type.str2int(x.as_py()) for x in array]
                new_columns[col] = pa.array(encoded_values, type=pa.int64())

                types[col] = cat_type
            except KeyError as e:
                raise ValueError(
                    f"Value {e} not found in encoding for column '{col}'"
                ) from e
        else:
            # If no encoding is provided, keep the original column
            new_columns[col] = array
    return modify_table(dataset, columns=new_columns, types=types)


def vectorize_text(
    dataset: DashAIDataset,
) -> DashAIDataset:
    """Convert text columns from the DashAIDataset to vectorized columns."""
    new_columns = {}
    table = dataset.arrow_table
    for col, _type in dataset.types.items():
        array = table[col]
        if isinstance(_type, Text):
            # Assuming a simple vectorization by splitting on spaces
            # In practice, you might want to use more sophisticated methods
            # like TF-IDF or word embeddings
            new_columns[col] = pa.array(
                [x.split() if x is not None else [] for x in array],
                type=pa.list_(pa.string()),
            )
        else:
            new_columns[col] = pa.array(array, type=to_arrow_types(_type.dtype))
    transformed_dataset = modify_table(dataset, columns=new_columns)
    return transformed_dataset


# Time Transformations

# Date Transformations


# Image Transformations
