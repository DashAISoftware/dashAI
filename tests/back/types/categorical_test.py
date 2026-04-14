import pyarrow as pa

from DashAI.back.types.categorical import Categorical


def test_categorical_init_string():
    categories = ["cat", "dog", "mouse"]
    test_array = pa.array(categories, from_pandas=True)

    cat = Categorical(values=test_array)

    assert cat.num_categories() == len(categories)

    s = cat.to_string()
    assert s["type"] == "Categorical"
    assert s["num_categories"] == len(categories)
    assert s["categories"] == [str(v) for v in categories]

    # Encodings

    for idx in range(len(categories)):
        key = cat.int2str(idx)
        assert cat.str2int(key) == idx

    # custom encoding
    custom_encoding = dict(enumerate(reversed(categories)))
    custom_cat = Categorical(values=test_array, encoding=custom_encoding)

    for exp_index, value in custom_encoding.items():
        assert custom_cat.str2int(value) == exp_index
        assert custom_cat.int2str(exp_index) == value


def test_categorical_init_int():
    categories = [1, 2, 3, 4, 5]
    test_array = pa.array(categories, from_pandas=True)

    cat = Categorical(values=test_array)

    assert cat.num_categories() == len(categories)

    s = cat.to_string()
    assert s["type"] == "Categorical"
    assert s["num_categories"] == len(categories)
    assert s["categories"] == [str(v) for v in categories]

    for i in range(len(categories)):
        label = cat.int2str(i)
        assert cat.str2int(label) == i

    custom_encoding = {value: i for i, value in enumerate(reversed(categories))}
    custom_cat = Categorical(values=test_array, encoding=custom_encoding)

    for value, exp_index in custom_encoding.items():
        assert custom_cat.str2int(value) == exp_index
        assert custom_cat.int2str(exp_index) == value


def test_categorical_encoder_default_string():
    """String categories default to one_hot encoder."""
    categories = ["cat", "dog", "mouse"]
    cat = Categorical(values=categories)
    assert cat.encoder == "one_hot"
    s = cat.to_string()
    assert s["encoder"] == "one_hot"


def test_categorical_encoder_default_int():
    """Integer categories default to one_hot (inference is in inference_methods, not here)."""
    categories = [1, 2, 3]
    cat = Categorical(values=categories)
    assert cat.encoder == "one_hot"
    s = cat.to_string()
    assert s["encoder"] == "one_hot"


def test_categorical_encoder_explicit():
    """Explicitly passed encoder is stored."""
    cat = Categorical(values=["a", "b"], encoder="label")
    assert cat.encoder == "label"
    assert cat.to_string()["encoder"] == "label"


def test_categorical_encoder_survives_arrow_roundtrip():
    """Encoder persists through to_string() → save_types_in_arrow_metadata()
    → get_types_from_arrow_metadata() round-trip."""
    import pyarrow as pa
    from DashAI.back.types.utils import (
        get_types_from_arrow_metadata,
        save_types_in_arrow_metadata,
    )

    cat = Categorical(values=["a", "b", "c"], encoder="label")
    types_dict = {"col1": cat.to_string()}

    table = pa.table({"col1": pa.array(["a", "b", "c"])})
    table_with_meta = save_types_in_arrow_metadata(table, types_dict)

    recovered = get_types_from_arrow_metadata(table_with_meta)
    assert isinstance(recovered["col1"], Categorical)
    assert recovered["col1"].encoder == "label"


def test_categorical_encoder_get_columns_spec(tmp_path):
    """get_columns_spec() returns encoder for Categorical columns."""
    import pyarrow as pa
    import pyarrow.ipc as ipc
    from DashAI.back.types.utils import save_types_in_arrow_metadata
    from DashAI.back.dataloaders.classes.dashai_dataset import get_columns_spec

    cat = Categorical(values=["x", "y"], encoder="label")
    types_dict = {"species": cat.to_string()}

    table = pa.table({"species": pa.array(["x", "y"])})
    table_with_meta = save_types_in_arrow_metadata(table, types_dict)

    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    arrow_path = str(dataset_dir / "data.arrow")
    with pa.OSFile(arrow_path, "wb") as sink:
        writer = ipc.new_file(sink, table_with_meta.schema)
        writer.write_table(table_with_meta)
        writer.close()

    spec = get_columns_spec(str(dataset_dir))
    assert spec["species"]["encoder"] == "label"


def test_categorical_encoder_missing_key_defaults_to_one_hot(tmp_path):
    """Old Arrow files with no encoder key in metadata default to one_hot."""
    import json
    import pyarrow as pa
    import pyarrow.ipc as ipc
    from DashAI.back.dataloaders.classes.dashai_dataset import get_columns_spec

    # Manually craft metadata without "encoder" key (simulates pre-feature Arrow file)
    types_dict = {
        "col": {
            "type": "Categorical",
            "categories": ["a", "b"],
            "num_categories": 2,
            "converted": False,
            "dtype": "string",
        }
    }
    table = pa.table({"col": pa.array(["a", "b"])})
    meta = dict(table.schema.metadata or {})
    meta[b"dashai_types"] = json.dumps(types_dict).encode()
    table = table.replace_schema_metadata(meta)

    dataset_dir = tmp_path / "ds"
    dataset_dir.mkdir()
    with pa.OSFile(str(dataset_dir / "data.arrow"), "wb") as sink:
        writer = ipc.new_file(sink, table.schema)
        writer.write_table(table)
        writer.close()

    spec = get_columns_spec(str(dataset_dir))
    assert spec["col"]["encoder"] == "one_hot"
