"""DashAI Dataset implementation."""

import json
import logging
import os
from contextlib import suppress

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc
from beartype import beartype
from beartype.typing import Dict, List, Literal, Optional, Tuple, Union
from datasets import ClassLabel, Dataset, DatasetDict, Value, concatenate_datasets
from pandas import DataFrame
from sklearn.model_selection import train_test_split

from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.utils import (
    arrow_to_dashai_types,
    comma_float_to_float,
    get_types_from_arrow_metadata,
    save_types_in_arrow_metadata,
    to_arrow_types,
)

log = logging.getLogger(__name__)


def get_arrow_table(ds: Dataset) -> pa.Table:
    """
    Retrieve the underlying PyArrow table from a Hugging Face Dataset.
    This function abstracts away the need to access private attributes.

    Parameters:
        ds (Dataset): A Hugging Face Dataset.

    Returns:
        pa.Table: The underlying PyArrow table.

    Raises:
        ValueError: If the arrow table cannot be retrieved.
    """
    if hasattr(ds, "arrow_table"):
        return ds.arrow_table
    elif hasattr(ds, "data") and hasattr(ds.data, "table"):
        return ds.data.table
    else:
        raise ValueError("Unable to retrieve underlying arrow table from the dataset.")


class DashAIDataset(Dataset):
    """DashAI dataset wrapper for Huggingface datasets with extra metadata."""

    @beartype
    def __init__(
        self,
        table: pa.Table,
        splits: dict = None,
        types: Dict[str, DashAIDataType] = None,
        *args,
        **kwargs,
    ):
        """Initialize a new instance of a DashAI dataset.

        Parameters
        ----------
        table : Table
            Arrow table from which the dataset will be created
        """
        super().__init__(table, *args, **kwargs)
        self.splits = splits or {}
        self._table = table
        self._types = (
            get_types_from_arrow_metadata(self._table) if types is None else types
        )

    @property
    def types(self):
        """Get the types of the dataset."""
        return self._types

    @types.setter
    def types(self, value):
        self._types = value

    @beartype
    def cast(self, *args, **kwargs) -> "DashAIDataset":
        """Override of the cast method to leave it in DashAI dataset format.

        Returns
        -------
        DatasetDashAI
            Dataset after cast
        """
        ds = super().cast(*args, **kwargs)
        arrow_tbl = get_arrow_table(ds)
        return DashAIDataset(arrow_tbl, splits=self.splits, types=self._types)

    @property
    def arrow_table(self) -> pa.Table:
        """
        Provides a clean way to access the underlying PyArrow table.

        Returns:
            pa.Table: The underlying PyArrow table.
        """
        try:
            # Now we reference  the pa.table from here (DashAIDataset)
            # and not the huggingface dataset, so we preserve the metadata
            return self._table
        except AttributeError:
            raise ValueError("Unable to retrieve the underlying Arrow table.") from None

    def keys(self) -> List[str]:
        """Return the available splits in the dataset.

        Returns
        -------
        List[str]
            List of split names (e.g., ['train', 'test', 'validation'])
        """
        if "split_indices" in self.splits:
            return list(self.splits["split_indices"].keys())
        return []

    # This method is still used only because Image dataset load
    # haven't been implemented to be DashAITypes compatible
    # So categories can't be labeled as Categorical Datatype
    # Should be removed ASAP when DashAIImageType and its handlers are implemented
    @beartype
    def change_columns_type(self, column_types: Dict[str, str]) -> "DashAIDataset":
        """Change the type of some columns.

        Note: this is a temporal method, and it will probably will delete in the future.

        Parameters
        ----------
        column_types : Dict[str, str]
            dictionary whose keys are the names of the columns to be changed and the
            values the new types.

        Returns
        -------
        DashAIDataset
            The dataset after columns type changes.
        """
        if not isinstance(column_types, dict):
            raise TypeError(f"types should be a dict, got {type(column_types)}")

        for column in column_types:
            if column in self.column_names:
                pass
            else:
                raise ValueError(
                    f"Error while changing column types: column '{column}' does not "
                    "exist in dataset."
                )
        new_features = self.features.copy()
        for column in column_types:
            if column_types[column] == "Categorical":
                new_features[column] = encode_labels(self, column)
            elif column_types[column] == "Numerical":
                new_features[column] = Value("float32")
        dataset = self.cast(new_features)
        return dataset

    def nan_per_column(self) -> "DashAIDataset":
        """Calculate the number of NaN values per column in the dataset and
        add it to the metadata under the 'nan' key.

        Parameters
        ----------
        None

        Returns
        -------
        DashAIDataset
            The dataset with the updated metadata.
        """
        dataset_df = self.to_pandas()
        # Calculate the number of NaN values per column
        nan_count = dataset_df.isna().sum().to_dict()
        self.splits.update({"nan": nan_count})

        return self

    @beartype
    def remove_columns(self, column_names: Union[str, List[str]]) -> "DashAIDataset":
        """Remove one or several column(s) in the dataset and the features
        associated to them.

        Parameters
        ----------
        column_names : Union[str, List[str]]
            Name, or list of names of columns to be removed.

        Returns
        -------
        DashAIDataset
            The dataset after columns removal.
        """
        if isinstance(column_names, str):
            column_names = [column_names]

        # Remove column from features
        modified_dataset = super().remove_columns(column_names)
        # Update self with modified dataset attributes
        self.__dict__.update(modified_dataset.__dict__)

        return self

    @beartype
    def sample(
        self,
        n: int = 1,
        method: Literal["head", "tail", "random"] = "head",  # noqa
        seed: Union[int, None] = None,
    ) -> Dict[str, List]:
        """Return sample rows from dataset.

        Parameters
        ----------
        n : int
            number of samples to return.
        method: Literal[str]
            method for selecting samples. Possible values are: 'head' to
            select the first n samples, 'tail' to select the last n samples
            and 'random' to select n random samples.
        seed : int, optional
            seed for random number generator when using 'random' method.

        Returns
        -------
        Dict
            A dictionary with selected samples.
        """
        if n > len(self):
            raise ValueError(
                "Number of samples must be less than or equal to the length "
                f"of the dataset. Number of samples: {n}, "
                f"dataset length: {len(self)}"
            )

        if method == "random":
            rng = np.random.default_rng(seed=seed)
            indexes = rng.integers(low=0, high=(len(self) - 1), size=n)
            sample = self.select(indexes).to_dict()

        elif method == "head":
            sample = self[:n]

        elif method == "tail":
            sample = self[-n:]

        return sample

    @beartype
    def get_split(self, split_name: str) -> "DashAIDataset":
        """
        Returns a new DashAIDataset corresponding to the specified split.
        This method uses the metadata 'split_indices' stored in the original
        DashAIDataset to obtain the list of indices for the desired split, then
        it creates a new dataset containing only those rows.

        Parameters:
            split_name (str): The name of the split to extract (e.g., "train",
            "test", "validation").

        Returns:
            DashAIDataset: A new DashAIDataset instance containing only the
            rows of the specified split.

        Raises:
            ValueError: If the specified split is not found in the splits
            of the dataset.
        """
        splits = self.splits.get("split_indices", {})
        if split_name not in splits:
            raise ValueError(f"Split '{split_name}' not found in dataset splits.")

        indices = splits[split_name]
        subset = self.select(indices)

        new_splits = {"split_indices": {split_name: indices}}
        arrow_table = subset.arrow_table  # with_format("arrow")[:] ####Check
        subset = DashAIDataset(arrow_table, splits=new_splits)
        return subset

    @beartype
    def select_columns(self, column_names: Union[str, List[str]]) -> "DashAIDataset":
        """
        Selects specific columns from the dataset and returns a new DashAIDataset
        containing only those columns.

        Parameters:
            column_names (Union[str, List[str]]): The name or list of names of the
            columns to select.

        Returns:
            DashAIDataset: A new DashAIDataset instance containing only the
            specified columns.
        """
        if isinstance(column_names, str):
            column_names = [column_names]

        subset_table = self.arrow_table.select(column_names)
        subset_types = {
            col: self._types[col] for col in column_names if col in self._types
        }

        return DashAIDataset(table=subset_table, splits=self.splits, types=subset_types)

    @beartype
    def select(self, *args, **kwargs) -> "DashAIDataset":
        """
        Selects rows from the dataset based on the provided indices or boolean mask.

        Parameters:
            *args: Positional arguments for selection.
            **kwargs: Keyword arguments for selection.

        Returns:
            DashAIDataset: A new DashAIDataset instance containing the selected rows.
        """
        selected_dataset = super().select(*args, **kwargs)
        if isinstance(selected_dataset, DashAIDataset):
            return selected_dataset
        else:
            # If the selected dataset is a Dataset, convert it to DashAIDataset
            arrow_tbl = selected_dataset.with_format("arrow")[:]
            arrow_tblx = save_types_in_arrow_metadata(
                arrow_tbl, {col: self._types[col].to_string() for col in self._types}
            )
            return DashAIDataset(arrow_tblx, types=self._types)


@beartype
def merge_splits_with_metadata(dataset_dict: DatasetDict) -> DashAIDataset:
    """
    Merges the splits from a DatasetDict into a single DashAIDataset and records
    the original indices for each split in the metadata.

    Parameters:
        dataset_dict (DatasetDict): A Hugging Face DatasetDict containing
        multiple splits.

    Returns:
        DashAIDataset: A unified dataset with merged data and metadata containing the
        original split indices.
    """

    concatenated_datasets = []
    split_index = {}
    current_index = 0

    if len(dataset_dict.keys()) == 1:
        arrow_tbl = get_arrow_table(dataset_dict["train"])
        return DashAIDataset(arrow_tbl)

    for split in sorted(dataset_dict.keys()):
        ds = dataset_dict[split]
        n_rows = len(ds)
        split_index[split] = list(range(current_index, current_index + n_rows))
        current_index += n_rows
        concatenated_datasets.append(ds)
    merged_dataset = concatenate_datasets(concatenated_datasets)
    arrow_tbl = get_arrow_table(merged_dataset)

    dashai_metadata = get_arrow_table(dataset_dict["train"]).schema.metadata.get(
        b"dashai_types", None
    )
    # We overwrite the metadata with the original DashAI types
    # because concatenate_datasets resets it to the huggingface default
    if dashai_metadata is not None:
        new_metadata = dict(arrow_tbl.schema.metadata)
        new_metadata[b"dashai_types"] = dashai_metadata
        arrow_tbl = arrow_tbl.replace_schema_metadata(new_metadata)

    dashai_dataset = DashAIDataset(arrow_tbl, splits={"split_indices": split_index})

    return dashai_dataset


@beartype
def transform_dataset_with_schema(
    dataset: DashAIDataset, schema: Dict[str, Dict]
) -> DashAIDataset:
    """
    Transform dataset columns according to the specified schema.

    This function processes each column in the dataset according to the type information
    provided in the schema, converting data types as needed and updating the dataset's
    type metadata.

    Parameters
    ----------
    dataset : DashAIDataset
        The dataset to transform
    schema : Dict[str, Dict]
        Dictionary mapping column names to type information

    Returns
    -------
    DashAIDataset
        - The updated dataset with new type information
    """
    table = get_arrow_table(dataset)
    dai_table = {}
    my_schema = pa.schema([])
    dashai_types = {}

    for column_name, info in schema.items():
        _type = info.get("type")
        dtype = info.get("dtype")
        pa_type = to_arrow_types(dtype)
        if _type == "Categorical":
            base_col = table.column(column_name)
            str_col = pa.array([str(x) for x in base_col.to_pylist()], type=pa.string())
            values = sorted(set(str_col.to_pylist()))
            dashai_types[column_name] = Categorical(values=values)
            dai_table[column_name] = str_col
            pa_type = to_arrow_types("string")
        # DashAIImage is currently not fully implemented
        # This step should be formalized after solving that.
        # elif _type == "Image": # noqa: ERA001
        #    pass # noqa: ERA001
        else:
            if _type in ["Date", "Time", "Timestamp"]:
                # Since DashAI is not using date, time or timestamp types for its models
                # we are saving them as strings to preserve the original format.
                # Can modify classes in value_types.py
                # if want to use PyArrow date, time or timestamp types.
                dashai_types[column_name] = arrow_to_dashai_types(
                    arrow_type=_type, format=dtype
                )
                pa_type = to_arrow_types("string")
                dai_table[column_name] = table.column(column_name)

            elif _type == "Float":
                dashai_types[column_name] = arrow_to_dashai_types(pa_type)
                dai_table[column_name] = comma_float_to_float(table.column(column_name))

            else:
                dashai_types[column_name] = arrow_to_dashai_types(pa_type)
                dai_table[column_name] = table.column(column_name)

        my_schema = my_schema.append(pa.field(column_name, pa_type))

    # Create the transformed table with the new schema
    transformed_table = pa.table(dai_table)
    transformed_table = transformed_table.cast(target_schema=my_schema)

    # Update dataset types
    dataset._types = dashai_types

    # Save types in arrow metadata
    types = {col: dashai_types[col].to_string() for col in dashai_types}
    transformed_table = save_types_in_arrow_metadata(transformed_table, types)

    return DashAIDataset(transformed_table, splits=dataset.splits, types=dashai_types)


@beartype
def save_dataset(
    dataset: DashAIDataset, path: Union[str, os.PathLike], schema=None
) -> None:
    """
    Saves a DashAIDataset in a custom format using two files in the specified directory:
      - "data.arrow": contains the dataset's PyArrow table.
      - "splits.json": contains the dataset's splits indices.

    Parameters:
        dataset (DashAIDataset): The dataset to save.
        path (Union[str, os.PathLike]): The directory path where the files
        will be saved.
    """

    os.makedirs(path, exist_ok=True)
    if schema is not None:
        dataset = transform_dataset_with_schema(dataset, schema)

    table = get_arrow_table(dataset)
    data_filepath = os.path.join(path, "data.arrow")
    with pa.OSFile(data_filepath, "wb") as sink:
        writer = ipc.new_file(sink, table.schema)
        writer.write_table(table)
        writer.close()

    metadata_filepath = os.path.join(path, "splits.json")
    metadata = dataset.splits
    metadata.update(
        {
            "total_rows": dataset.shape[0],
            "column_names": dataset.column_names,
        }
    )

    with open(metadata_filepath, "w") as f:
        json.dump(metadata, f, indent=2, sort_keys=True, ensure_ascii=False)


@beartype
def load_dataset(dataset_path: Union[str, os.PathLike]) -> DashAIDataset:
    """
    Loads a DashAIDataset previously saved with save_dataset.

    It expects the directory at 'path' to contain:
        - "data.arrow": the saved PyArrow table.
        - "splits.json": the saved split indices.

    Parameters:
        path (Union[str, os.PathLike]): The directory path where the dataset was saved.

    Returns:
        DashAIDataset: The loaded dataset with data and metadata.
    """

    data_filepath = os.path.join(dataset_path, "data.arrow")
    with pa.OSFile(data_filepath, "rb") as source:
        reader = ipc.open_file(source)
        data = reader.read_all()
    metadata_filepath = os.path.join(dataset_path, "splits.json")
    if os.path.exists(metadata_filepath):
        with open(metadata_filepath, "r") as f:
            splits = json.load(f)
    else:
        splits = {}
    return DashAIDataset(data, splits=splits)


# Use it only for Image classification
# since images are loaded different to tabular data
# And it's link to DashAIDataTypes is not implemented yet
# So categorical columns can't be labeled as Categorical Datatype but ClassLabel
# Should be removed ASAP when DashAIImageType and its handlers are implemented
@beartype
def encode_labels(
    dataset: DashAIDataset,
    column_name: str,
) -> ClassLabel:
    """Encode a categorical column into numerical labels and
    return the ClassLabel feature.

    Parameters
    ----------
    dataset : DashAIDataset
        Dataset containing the column to encode.
    column_name : str
        Name of the column to encode.

    Returns
    -------
    ClassLabel
        The ClassLabel feature with the mapping of labels to integers.
    """
    if column_name not in dataset.column_names:
        raise ValueError(f"Column '{column_name}' does not exist in the dataset.")

    names = list(set(dataset[column_name]))
    class_label_feature = ClassLabel(names=names)
    return class_label_feature


@beartype
def check_split_values(
    train_size: float,
    test_size: float,
    val_size: float,
) -> None:
    if train_size < 0 or train_size > 1:
        raise ValueError(
            "train_size should be in the (0, 1) range "
            f"(0 and 1 not included), got {val_size}"
        )
    if test_size < 0 or test_size > 1:
        raise ValueError(
            "test_size should be in the (0, 1) range "
            f"(0 and 1 not included), got {val_size}"
        )
    if val_size < 0 or val_size > 1:
        raise ValueError(
            "val_size should be in the (0, 1) range "
            f"(0 and 1 not included), got {val_size}"
        )


@beartype
def split_indexes(
    total_rows: int,
    train_size: float,
    test_size: float,
    val_size: float,
    seed: Union[int, None] = None,
    shuffle: bool = True,
    stratify: bool = False,
    labels: Union[List, None] = None,
) -> Tuple[List, List, List]:
    """Generate lists with train, test and validation indexes.

    The algorithm for splitting the dataset is as follows:

    1. The dataset is divided into a training and a test-validation split
        (sum of test_size and val_size).
    2. The test and validation set is generated from the test-validation set,
        where the size of the test-validation set is now considered to be 100%.
        Therefore, the sizes of the test and validation sets will now be
        calculated as 100%, i.e. as val_size/(test_size+val_size) and
        test_size/(test_size+val_size) respectively.

    Example:

    If we split a dataset into 0.8 training, a 0.1 test, and a 0.1 validation,
    in the first process we split the training data with 80% of the data, and
    the test-validation data with the remaining 20%; and then in the second
    process we split this 20% into 50% test and 50% validation.

    Parameters
    ----------
    total_rows : int
        Size of the Dataset.
    train_size : float
        Proportion of the dataset for train split (in 0-1).
    test_size : float
        Proportion of the dataset for test split (in 0-1).
    val_size : float
        Proportion of the dataset for validation split (in 0-1).
    seed : Union[int, None], optional
        Set seed to control to enable replicability, by default None
    shuffle : bool, optional
        If True, the data will be shuffled when splitting the dataset,
        by default True.
    stratify : bool, optional
        If True, the data will be stratified when splitting the dataset,
        by default False.

    Returns
    -------
    Tuple[List, List, List]
        Train, Test and Validation indexes.
    """

    # Generate shuffled indexes
    if seed is None:
        seed = 42
    indexes = np.arange(total_rows)

    test_val = test_size + val_size
    val_proportion = test_size / test_val

    stratify_labels = np.array(labels) if stratify else None

    train_indexes, test_val_indexes = train_test_split(
        indexes,
        train_size=train_size,
        random_state=seed,
        shuffle=shuffle,
        stratify=stratify_labels,
    )

    stratify_labels_test_val = stratify_labels[test_val_indexes] if stratify else None

    test_indexes, val_indexes = train_test_split(
        test_val_indexes,
        train_size=val_proportion,
        random_state=seed,
        shuffle=shuffle,
        stratify=stratify_labels_test_val,
    )
    return train_indexes.tolist(), test_indexes.tolist(), val_indexes.tolist()


@beartype
def split_dataset(
    dataset: DashAIDataset,
    train_indexes: List = None,
    test_indexes: List = None,
    val_indexes: List = None,
) -> DatasetDict:
    """
    Split the dataset in train, test and validation subsets.
    If indexes are not provided, it will use the split indices
    from the dataset's splits.

    Parameters
    ----------
    dataset : DashAIDataset
        A HuggingFace DashAIDataset containing the dataset to be split.
    train_indexes : List, optional
        Train split indexes. If None, uses indices from splits.
    test_indexes : List, optional
        Test split indexes. If None, uses indices from splits.
    val_indexes : List, optional
        Validation split indexes. If None, uses indices from splits.

    Returns
    -------
    DatasetDict
        The split dataset.

    Raises
    -------
    ValueError
        Must provide all indexes or none.
    """
    if all(idx is None for idx in [train_indexes, test_indexes, val_indexes]):
        train_dataset = dataset.get_split("train")
        test_dataset = dataset.get_split("test")
        val_dataset = dataset.get_split("validation")
        return DatasetDict(
            {
                "train": train_dataset,
                "test": test_dataset,
                "validation": val_dataset,
            }
        )
    elif any(idx is None for idx in [train_indexes, test_indexes, val_indexes]):
        raise ValueError("Must provide all indexes or none.")

    # Get the number of records
    n = len(dataset)

    # Convert the indexes into boolean masks
    train_mask = np.isin(np.arange(n), train_indexes)
    test_mask = np.isin(np.arange(n), test_indexes)
    val_mask = np.isin(np.arange(n), val_indexes)

    # Get the underlying table
    table = dataset.arrow_table

    dataset.splits["split_indices"] = {
        "train": train_indexes,
        "test": test_indexes,
        "validation": val_indexes,
    }

    # Create separate tables for each split
    train_table = table.filter(pa.array(train_mask))
    test_table = table.filter(pa.array(test_mask))
    val_table = table.filter(pa.array(val_mask))

    separate_dataset_dict = DatasetDict(
        {
            "train": DashAIDataset(train_table),
            "test": DashAIDataset(test_table),
            "validation": DashAIDataset(val_table),
        }
    )

    return separate_dataset_dict


def to_dashai_dataset(
    dataset: Union[DatasetDict, Dataset, DashAIDataset, DataFrame],
) -> DashAIDataset:
    """
    Converts various data formats into a unified DashAIDataset.

    Parameters:
        dataset: The original dataset which can be one of:
            - DatasetDict: A Hugging Face DatasetDict
            - Dataset: A Hugging Face Dataset
            - DashAIDataset: Already a DashAIDataset (will be returned as is)
            - pd.DataFrame: A pandas DataFrame

    Returns:
        DashAIDataset: A unified dataset containing all data.
    """

    if isinstance(dataset, DashAIDataset):
        # If is already a DashAIDataset, return it
        return dataset

    if isinstance(dataset, Dataset):
        # If is a Dataset, convert it to DashAIDataset
        arrow_tbl = get_arrow_table(dataset)
        return DashAIDataset(arrow_tbl)
    if isinstance(dataset, DataFrame):
        hf_dataset = Dataset.from_pandas(dataset)
        arrow_tbl = get_arrow_table(hf_dataset)
        return DashAIDataset(arrow_tbl)
    if isinstance(dataset, DatasetDict) and len(dataset) == 1:
        key = list(dataset.keys())[0]
        ds = dataset[key]
        arrow_tbl = get_arrow_table(ds)
        return DashAIDataset(arrow_tbl)
    if isinstance(dataset, DatasetDict):
        return merge_splits_with_metadata(dataset)
    else:
        raise TypeError(f"Unsupported dataset type: {type(dataset)}")


@beartype
def validate_inputs_outputs(
    datasetdict: Union[DatasetDict, DashAIDataset],
    inputs: List[str],
    outputs: List[str],
) -> None:
    """Validate the columns to be chosen as input and output.
    The algorithm considers those that already exist in the dataset.

    Parameters
    ----------
    names : List[str]
        Dataset column names.
    inputs : List[str]
        List of input column names.
    outputs : List[str]
        List of output column names.
    """
    datasetdict = to_dashai_dataset(datasetdict)
    dataset_features = list((datasetdict.features).keys())
    if len(inputs) == 0 or len(outputs) == 0:
        raise ValueError(
            "Inputs and outputs columns lists to validate must not be empty"
        )
    if len(inputs) + len(outputs) > len(dataset_features):
        raise ValueError(
            "Inputs and outputs cannot have more elements than names. "
            f"Number of inputs: {len(inputs)}, "
            f"number of outputs: {len(outputs)}, "
            f"number of names: {len(dataset_features)}. "
        )
        # Validate that inputs and outputs only contain elements that exist in names
    if not set(dataset_features).issuperset(set(inputs + outputs)):
        raise ValueError(
            f"Inputs and outputs can only contain elements that exist in names. "
            f"Extra elements: "
            f"{', '.join(set(inputs + outputs).difference(set(dataset_features)))}"
        )


@beartype
def get_column_names_from_indexes(
    dataset: Union[DashAIDataset, DatasetDict], indexes: List[int]
) -> List[str]:
    """Obtain the column labels that correspond to the provided indexes.

    Note: indexing starts from 1.

    Parameters
    ----------
    datasetdict : DatasetDict
        Path where the dataset is stored.
    indices : List[int]
        List with the indices of the columns.

    Returns
    -------
    List[str]
        List with the labels of the columns
    """
    dataset = to_dashai_dataset(dataset)

    dataset_features = list((dataset.features).keys())
    col_names = []
    for index in indexes:
        if index > len(dataset_features):
            raise ValueError(
                f"The list of indices can only contain elements within"
                f" the amount of columns. "
                f"Index {index} is greater than the total of columns."
            )
        col_names.append(dataset_features[index - 1])
    return col_names


@beartype
def select_columns(
    dataset: Union[DatasetDict, DashAIDataset],
    input_columns: List[str],
    output_columns: List[str],
) -> Tuple[DashAIDataset, DashAIDataset]:
    """Divide the dataset into a dataset with only the input columns in it
    and other dataset only with the output columns

    Parameters
    ----------
    dataset : Union[DatasetDict, DashAIDataset]
        Dataset to divide
    input_columns : List[str]
        List with the input columns labels
    output_columns : List[str]
        List with the output columns labels

    Returns
    -------
    DashAIDataset
        Tuple with the separated datasets x and y
    """
    dataset = to_dashai_dataset(dataset)
    input_columns_dataset = dataset.select_columns(input_columns)
    output_columns_dataset = dataset.select_columns(output_columns)
    return (input_columns_dataset, output_columns_dataset)


@beartype
def get_columns_spec(dataset_path: str) -> Dict[str, Dict]:
    """Return the column with their respective types.


    Parameters
    ----------
    dataset_path : str
        Path where the dataset is stored.

    Returns
    -------
    Dict
        Dict with the columns and types
    """
    dataset = load_dataset(dataset_path)

    column_types = {}
    for column in dataset.types:
        column_spec = dataset.types[column]
        dtype = column_spec.to_string().get("dtype", None)
        _format = column_spec.to_string().get("format", None)
        column_types[column] = {
            "type": column_spec.to_string().get("type", None),
            "dtype": _format if _format else dtype,
        }
    return column_types


# Not currently used
@beartype
def update_columns_spec(dataset_path: str, columns: Dict) -> DashAIDataset:
    """Update the column specification of some dataset on secondary memory.

    If the column type isn't a Value or ClassLabel, the function will
    not change the type of the column.

    Parameters
    ----------
    dataset_path : str
        Path where the dataset is stored.
    columns : Dict
        Dict with columns and types to change

    Returns
    -------
    Dict
        Dict with the columns and types
    """
    if not isinstance(columns, dict):
        raise TypeError(f"types should be a dict, got {type(columns)}")

    # load the dataset from where its stored
    dataset = load_dataset(dataset_path)
    # copy the features with the columns ans types
    new_features = dataset.features
    for column in columns:
        if columns[column].type == "ClassLabel" or columns[column].type == "Value":
            pass

        # cast the column types with the changes
        try:
            dataset = dataset.cast(new_features)

        except ValueError as e:
            raise ValueError("Error while trying to cast the columns") from e
    return dataset


def get_dataset_info(dataset_path: str) -> object:
    """Return the info of the dataset with the number of rows,
    number of columns and splits size.

    Parameters
    ----------
    dataset_path : str
        Path where the dataset is stored.

    Returns
    -------
    object
        Dictionary with the information of the dataset
    """
    metadata_filepath = os.path.join(dataset_path, "splits.json")
    if os.path.exists(metadata_filepath):
        with open(metadata_filepath, "r") as f:
            splits_data = json.load(f)
    else:
        splits_data = {"split_indices": {}}

    splits = splits_data.get("split_indices", {})
    train_indices = splits.get("train", [])
    test_indices = splits.get("test", [])
    val_indices = splits.get("validation", [])
    total_rows = splits_data.get("total_rows", 0)
    column_names = splits_data.get("column_names", [])

    return {
        "total_rows": total_rows,
        "total_columns": len(column_names),
        "column_names": column_names,
        "nan": splits_data.get("nan", {}),
        "train_size": len(train_indices),
        "test_size": len(test_indices),
        "val_size": len(val_indices),
        "train_indices": train_indices,
        "test_indices": test_indices,
        "val_indices": val_indices,
    }


@beartype
def update_dataset_splits(
    dataset: DashAIDataset, new_splits: object, is_random: bool
) -> DashAIDataset:
    """Update the metadata splits of a DashAIDataset. The splits could be random by
    giving numbers between 0 and 1 in new_splits parameters and setting the is_random
    parameter to True, or the could be manually selected by giving lists of indices
    to new_splits parameter and setting the is_random parameter to False.

    Args:
        dataset (DashAIDataset: Dataset to update splits
        new_splits (object): Object with the new train, test and validation config
        is_random (bool): If the new splits are random by percentage

    Returns:
        DashAIDataset: New DashAIDataset with the new splits configuration.
    """
    n = dataset.num_rows
    if is_random:
        check_split_values(
            new_splits["train"], new_splits["test"], new_splits["validation"]
        )
        train_indexes, test_indexes, val_indexes = split_indexes(
            n, new_splits["train"], new_splits["test"], new_splits["validation"]
        )
    else:
        train_indexes = new_splits["train"]
        test_indexes = new_splits["test"]
        val_indexes = new_splits["validation"]
    dataset.splits["split_indices"] = {
        "train": train_indexes,
        "test": test_indexes,
        "validation": val_indexes,
    }
    return dataset


# I'm not completely sure what this function does in converting categorical indexes part
# I think it could be simplified since DashAITypes, but I don't want to break anything
def prepare_for_experiment(
    dataset: DashAIDataset, splits: dict, output_columns: List[str]
) -> DatasetDict:
    """Prepare the dataset for an experiment by updating the splits configuration"""
    splitType = splits.get("splitType")
    if splitType == "manual" or splitType == "predefined":
        splits_index = splits
        prepared_dataset = split_dataset(
            dataset,
            train_indexes=splits_index["train"],
            test_indexes=splits_index["test"],
            val_indexes=splits_index["validation"],
        )
    else:
        n = len(dataset)
        labels = None
        if splits.get("stratify", False) and output_columns:
            output_column = output_columns[0]
            print("Stratifying by column:", output_column)
            column_type = dataset.types[output_column]
            print("Column type:", column_type)
            try:
                column_values = dataset[output_column]
                # Check column type and convert to numerical indices if needed
                if isinstance(column_type, Categorical):
                    with suppress(Exception):
                        labels = (
                            [column_type.str2int(v) for v in column_values]
                            if column_values
                            else []
                        )
                else:
                    labels = [
                        int(x) if not isinstance(x, (list, tuple)) else int(x[0])
                        for x in column_values
                    ]
            except Exception as e:
                raise ValueError(
                    f"Error while trying to stratify the dataset: {e}"
                ) from e

        train_indexes, test_indexes, val_indexes = split_indexes(
            n,
            splits["train"],
            splits["test"],
            splits["validation"],
            shuffle=splits.get("shuffle", False),
            seed=splits.get("seed"),
            stratify=splits.get("stratify", False),
            labels=labels,
        )
        prepared_dataset = split_dataset(
            dataset,
            train_indexes=train_indexes,
            test_indexes=test_indexes,
            val_indexes=val_indexes,
        )
    return prepared_dataset, {
        "train_indexes": train_indexes,
        "test_indexes": test_indexes,
        "val_indexes": val_indexes,
    }


def modify_table(
    dataset: DashAIDataset,
    columns: Dict[str, pa.Array],
    types: Optional[Dict[str, DashAIDataType]] = None,
) -> DashAIDataset:
    """
    Modifies the pa.table and its pa.type of a column in a DashAIDataset.
    This function serves as a tool for models to modify the data in order to process it.

    Parameters
    ----------
    dataset : DashAIDataset
        The dataset to modify.
    columns: dict[str, pa.Array]
        A dictionary where keys are column names and values are the new PyArrow arrays.

    Returns
    -------
    DashAIDataset
        The modified dataset with the updated column type.
    """
    original_table = dataset.arrow_table
    updated_columns = {}

    for name in dataset.column_names:
        if name in columns:
            updated_columns[name] = columns[name]
        else:
            updated_columns[name] = original_table[name]
    # In case new columns are added. Added purposely to deal with converters.
    for name in columns:
        if name not in dataset.column_names:
            if types is None or name not in types:
                raise ValueError(
                    f"Missing DashAI type for new column '{name}', "
                    f"check if converter provides it."
                )
            updated_columns[name] = columns[name]

    new_table = pa.table(updated_columns)

    new_table = new_table.replace_schema_metadata(original_table.schema.metadata)
    new_table = (
        save_types_in_arrow_metadata(
            new_table, {col: types[col].to_string() for col in types}
        )
        if types
        else new_table
    )

    new_types = types if types else dataset.types

    return DashAIDataset(new_table, splits=dataset.splits, types=new_types)
    return DashAIDataset(new_table, splits=dataset.splits, types=new_types)
