import copy

import pandas as pd
import pyarrow as pa

from DashAI.back.dataloaders.classes.dashai_dataset import (
    get_columns_spec,
    load_dataset,
    merge_splits_with_metadata,
    modify_table,
    prepare_for_model_session,
    save_dataset,
    to_dashai_dataset,
)
from DashAI.back.types.value_types import Text


def test_dashai_dataset_ops_types_persistance(tmp_path):
    iris_df = pd.DataFrame(
        {
            "SepalLengthCm": [5.1, 4.9, 4.7, 4.6, 5.0],
            "SepalWidthCm": [3.5, 3.0, 3.2, 3.1, 3.6],
            "PetalLengthCm": [1.4, 1.4, 1.3, 1.5, 1.4],
            "PetalWidthCm": [0.2, 0.2, 0.2, 0.2, 0.2],
            "Species": [
                "Iris-setosa",
                "Iris-setosa",
                "Iris-virginica",
                "Iris-virginica",
                "Iris-versicolor",
            ],
        }
    )

    dataset = to_dashai_dataset(iris_df)

    schema = {
        "SepalLengthCm": {"type": "Float", "dtype": "float64"},
        "SepalWidthCm": {"type": "Float", "dtype": "float64"},
        "PetalLengthCm": {"type": "Float", "dtype": "float64"},
        "PetalWidthCm": {"type": "Float", "dtype": "float64"},
        "Species": {"type": "Categorical", "dtype": "string"},
    }

    outdir = tmp_path / "save_ds"

    save_dataset(dataset, outdir, schema=schema)

    ds_loaded = load_dataset(outdir)

    float_cols = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
    categorical_cols = ["Species"]
    for col in float_cols:
        assert ds_loaded.types[col].to_string() == {"type": "Float", "dtype": "float64"}

    for col in categorical_cols:
        s_cat = ds_loaded.types[col].to_string()
        assert s_cat["type"] == "Categorical"
        assert set(s_cat["categories"]) == {
            "Iris-setosa",
            "Iris-virginica",
            "Iris-versicolor",
        }
        assert s_cat["num_categories"] == 3

    ####
    subset = ds_loaded.select_columns(["SepalLengthCm", "Species"])
    assert set(subset.column_names) == {"SepalLengthCm", "Species"}
    assert subset.types["SepalLengthCm"].to_string() == {
        "type": "Float",
        "dtype": "float64",
    }
    sub_cat = subset.types["Species"].to_string()
    assert sub_cat["type"] == "Categorical"
    assert set(sub_cat["categories"]) == {
        "Iris-setosa",
        "Iris-virginica",
        "Iris-versicolor",
    }
    assert sub_cat["num_categories"] == 3

    ####
    splits = {
        "splitType": "random",
        "train": 0.6,
        "test": 0.2,
        "validation": 0.2,
        "shuffle": True,
        "seed": 123,
        "stratify": False,
    }

    ds_prepared, _ = prepare_for_model_session(
        ds_loaded, splits=splits, output_columns=["Species"]
    )

    assert set(ds_prepared.keys()) == {"train", "test", "validation"}

    for split in ("train", "test", "validation"):
        assert ds_prepared[split].types["SepalLengthCm"].to_string() == {
            "type": "Float",
            "dtype": "float64",
        }
        assert ds_prepared[split].types["SepalWidthCm"].to_string() == {
            "type": "Float",
            "dtype": "float64",
        }
        assert ds_prepared[split].types["PetalLengthCm"].to_string() == {
            "type": "Float",
            "dtype": "float64",
        }
        assert ds_prepared[split].types["PetalWidthCm"].to_string() == {
            "type": "Float",
            "dtype": "float64",
        }
        sp_cat = ds_prepared[split].types["Species"].to_string()
        assert sp_cat["type"] == "Categorical"
        assert set(sp_cat["categories"]) == {
            "Iris-setosa",
            "Iris-virginica",
            "Iris-versicolor",
        }
        assert sp_cat["num_categories"] == 3

    ###

    ds_drop = ds_loaded.remove_columns(["PetalWidthCm"])

    assert "PetalWidthCm" not in ds_drop.column_names

    for col in ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "Species"]:
        if col == "Species":
            sp_cat = ds_drop.types[col].to_string()
            assert sp_cat["type"] == "Categorical"
            assert set(sp_cat["categories"]) == {
                "Iris-setosa",
                "Iris-virginica",
                "Iris-versicolor",
            }
            assert sp_cat["num_categories"] == 3

        else:
            assert ds_drop.types[col].to_string() == {
                "type": "Float",
                "dtype": "float64",
            }
    ###

    merged = merge_splits_with_metadata(ds_prepared)

    for col in ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]:
        assert merged.types[col].to_string() == {"type": "Float", "dtype": "float64"}

    sp_cat_merged = merged.types["Species"].to_string()
    assert sp_cat_merged["type"] == "Categorical"
    assert set(sp_cat_merged["categories"]) == {
        "Iris-setosa",
        "Iris-virginica",
        "Iris-versicolor",
    }
    assert sp_cat_merged["num_categories"] == 3


def test_get_columns_spec_types(tmp_path):
    spec_df = pd.DataFrame(
        {
            "int_col": [1, 2, 3, 4, 5],
            "float_col": [1.1, 2.2, 3.3, 4.4, 5.5],
            "cat_col": ["A", "B", "A", "C", "B"],
            "text_col": ["lorem", "ipsum", "dolor", "sit", "amet"],
        }
    )

    dataset = to_dashai_dataset(spec_df)

    schema = {
        "int_col": {"type": "Integer", "dtype": "int64"},
        "float_col": {"type": "Float", "dtype": "float64"},
        "cat_col": {"type": "Categorical", "dtype": "string"},
        "text_col": {"type": "Text", "dtype": "string"},
    }

    outdir = tmp_path / "spec_ds"

    save_dataset(dataset, outdir, schema=schema)
    spec = get_columns_spec(str(outdir))

    assert spec["int_col"] == {"type": "Integer", "dtype": "int64"}
    assert spec["float_col"] == {"type": "Float", "dtype": "float64"}
    assert spec["cat_col"]["type"] == "Categorical"
    assert spec["text_col"] == {"type": "Text", "dtype": "string"}


def test_modify_table_types(tmp_path):
    mod_df = pd.DataFrame(
        {
            "int_col": [1, 2, 3, 4, 5],
            "float_col": [1.0, 2.0, 3.0, 4.0, 5.0],
            "cat_col": ["A", "B", "A", "C", "B"],
            "text_col": ["lorem", "ipsum", "dolor", "sit", "amet"],
        }
    )

    dataset = to_dashai_dataset(mod_df)

    schema = {
        "int_col": {"type": "Integer", "dtype": "int64"},
        "float_col": {"type": "Float", "dtype": "float64"},
        "cat_col": {"type": "Categorical", "dtype": "string"},
        "text_col": {"type": "Text", "dtype": "string"},
    }

    outdir = tmp_path / "mod_ds"
    save_dataset(dataset, outdir, schema=schema)
    ds_loaded = load_dataset(outdir)

    new_col = pa.array([10, 20, 30, 40, 50], type=pa.int64())
    mod_ds = modify_table(ds_loaded, columns={"int_col": new_col})
    assert mod_ds.arrow_table["int_col"].to_pylist() == [10, 20, 30, 40, 50]
    assert mod_ds.types["int_col"].to_string() == {"type": "Integer", "dtype": "int64"}

    new_col_2 = pa.array(
        [str(x) for x in mod_ds.arrow_table["float_col"].to_pylist()], type=pa.string()
    )
    new_types = copy.deepcopy(mod_ds.types)
    new_types["float_col"] = Text(pa.string())

    mod_ds_2 = modify_table(mod_ds, columns={"float_col": new_col_2}, types=new_types)
    assert mod_ds_2.arrow_table["float_col"].to_pylist() == [
        "1.0",
        "2.0",
        "3.0",
        "4.0",
        "5.0",
    ]
    assert mod_ds_2.types["float_col"].to_string() == {
        "type": "Text",
        "encoding": "utf-8",
        "dtype": "string",
    }
    assert mod_ds_2.types["int_col"].to_string() == {
        "type": "Integer",
        "dtype": "int64",
    }
    assert mod_ds_2.types["cat_col"].to_string() == {
        "type": "Categorical",
        "categories": ["A", "B", "C"],
        "num_categories": 3,
        "converted": False,
        "dtype": "string",
        "encoder": "one_hot",
    }
    assert mod_ds_2.types["text_col"].to_string() == {
        "type": "Text",
        "encoding": "utf-8",
        "dtype": "string",
    }
