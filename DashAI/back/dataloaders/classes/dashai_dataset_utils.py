import numpy as np
import pandas as pd
import pyarrow as pa
from sklearn.preprocessing import OneHotEncoder
from typing import Dict, Union, Tuple
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset, modify_table
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.utils import save_types_in_arrow_metadata, to_arrow_types
from DashAI.back.types.value_types import (
    Binary,
    #Boolean,
    Date,
    Decimal,
    Duration,
    Float,
    Integer,
    Text,
    Time,
    Timestamp,
)

# This module provides utility functions to convert DashAIDataset to various formats when needed, as DashAIDataset should be the main data structure used in DashAI.
# If a new transformation is needed, it should be added here to allow further extensibility.

# Format Convertions


def dashai_to_pandas(
    dataset: DashAIDataset,
    squeeze: bool = False,
) -> pd.DataFrame:
    """Convert DashAIDataset to pandas DataFrame."""
    if squeeze:
        return dataset.to_pandas().squeeze()

    return dataset.to_pandas()


def dashai_to_numpy(
    dataset: DashAIDataset,
) -> np.ndarray:
    """Convert DashAIDataset to numpy array."""
    return dataset.to_numpy()


def dashai_to_dict(
    dataset: DashAIDataset,
) -> dict:
    """Convert DashAIDataset to dictionary."""
    return dataset.to_dict()


###### Data Transformations ######

# Categorical Transformations


def categorical_label_encoder(
    dataset: DashAIDataset,
) -> Tuple[DashAIDataset, Dict[str, Dict[str, int]]]:
    """Convert categorical columns from the DashAIDataset to label encoded integers.

    Parameters
    ----------
    dataset : DashAIDataset
        The dataset containing both non categorical and categorical columns to be label encoded.

    Returns
    -------
    DashAIDataset
        A new DashAIDataset with categorical columns converted to label encoded integers.
    encodings : dict
        A dictionary containing the encodings for each categorical column, where keys are column names and values.
    """
    new_columns = {}
    table = dataset.arrow_table
    encodings = {}

    for col, _type in dataset.types.items():

        array = table[col]
        # Check every column dashai_type to find the categorical ones
        if isinstance(_type, Categorical):
            values = [_type.str2int(x.as_py()) for x in array]
            new_columns[col] = pa.array(values, type=pa.int64())
            encodings[col] = dict(_type._str2int)  # Store the encoding for later use
        else:
            new_columns[col] = array

    return modify_table(dataset, columns=new_columns), encodings

#This function is used to apply the encodings stored in the model to the categorical columns in the dataset.
def apply_categorical_label_encoder(
    dataset: DashAIDataset,  encodings: Dict[str, Dict[str, int]]
) -> DashAIDataset:
    """Apply Model stored encodings to the categorical columns in the dataset.
    
    Parameters
    ----------
    dataset : DashAIDataset
        The dataset containing both non categorical and categorical columns to be label encoded.
    encodings : dict
        A dictionary containing the encodings for each categorical column, where keys are column names and values are dictionaries mapping original values to encoded integers.
    
    Returns
    -------
    DashAIDataset
        A new DashAIDataset with categorical columns converted to label encoded integers using the provided encodings.
    
    """

    table = dataset.arrow_table
    new_columns = {}
    types = dataset.types

    for col in table.column_names:
        array = table[col]
        _type = types[col]

        if col in encodings and isinstance(_type, Categorical):
            # Apply the stored encodings to the categorical columns

            encoding = encodings[col]
            try:
                encoded_values = [encoding[x.as_py()] for x in array]
                new_columns[col] = pa.array(encoded_values, type=pa.int64())

                categories = list(encoding.keys())
                types[col] = Categorical(categories, encoding=encoding)
            except KeyError as e:
                raise ValueError(f"Value {e} not found in encoding for column '{col}'") from e
        else:
            # If no encoding is provided, keep the original column
            new_columns[col] = array
    return modify_table(dataset, columns=new_columns, types=types)

def sklearn_one_hot_encoder(
    dataset: DashAIDataset,
) -> DashAIDataset:
    """Convert categorical columns from the DashAIDataset to one-hot encoded columns.

    Parameters
    ----------
    dataset : DashAIDataset
        The dataset containing both non categorical and categorical columns to be one-hot encoded.

    Returns
    -------
    DashAIDataset
        A new DashAIDataset with categorical columns converted to one-hot encoded columns.
    """
    table = dataset.arrow_table
    types = dataset.types
    metadata = table.schema.metadata

    cat_cols = [col for col, _type in types.items() if isinstance(_type, Categorical)]

    if not cat_cols:
        # If there are no categorical columns, return the original dataset
        return dataset

    df = dataset.to_pandas()
    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    encoded_array = encoder.fit_transform(df[cat_cols])
    encoded_columns = encoder.get_feature_names_out(cat_cols)

    encoded_df = pd.DataFrame(encoded_array, columns=encoded_columns)

    # Drop original categorical columns
    df = df.drop(columns=cat_cols, inplace=True)
    df = pd.concat([df, encoded_df], axis=1)

    new_table = pa.Table.from_pandas(df, preserve_index=False)

    for col in encoded_columns:
        types[col] = Categorical(encoded_df[col].unique().tolist())

    md_types = {}
    for col, _type in types.items():
        md_types[col] = _type.to_string()

    # Save the new types in the metadata
    new_table = save_types_in_arrow_metadata(new_table, md_types)

    # Create a new DashAIDataset with the modified table and types
    transformed_dataset = DashAIDataset(
        table=new_table,
        types=types,
    )

    return transformed_dataset


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
            # In practice, you might want to use more sophisticated methods like TF-IDF or word embeddings
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
