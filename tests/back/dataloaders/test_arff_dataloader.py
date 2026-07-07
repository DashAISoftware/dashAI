"""ARFF DataLoader tests module."""

import pathlib
from typing import Any, Dict

import pytest
from sklearn.datasets import load_diabetes, load_iris, load_wine

from DashAI.back.dataloaders.classes.arff_dataloader import ARFFDataLoader
from tests.back.dataloaders.base_tabular_dataloader_tests import (
    BaseTabularDataLoaderTester,
)
from tests.back.test_datasets_generator import ARFFTestDatasetGenerator


@pytest.fixture(scope="module", autouse=True)
def _setup(test_datasets_path: pathlib.Path, random_state: int) -> None:
    """Generate the ARFF test datasets."""
    df_iris = load_iris(return_X_y=False, as_frame=True)["frame"]  # type: ignore
    df_wine = load_wine(return_X_y=False, as_frame=True)["frame"]  # type: ignore
    df_diabetes = load_diabetes(return_X_y=False, as_frame=True)["frame"]  # type: ignore

    for df, name in [(df_iris, "iris"), (df_wine, "wine"), (df_diabetes, "diabetes")]:
        ARFFTestDatasetGenerator(
            df=df,
            dataset_name=name,
            ouptut_path=test_datasets_path,
            random_state=random_state,
        )


class TestARFFDataloader(BaseTabularDataLoaderTester):
    @property
    def dataloader_cls(self):
        return ARFFDataLoader

    @property
    def data_type_name(self):
        return "arff"

    @pytest.mark.parametrize(
        ("dataset_path", "params", "nrows", "ncols"),
        [
            ("iris/basic.arff", {}, 150, 5),
            ("wine/basic.arff", {}, 178, 14),
            ("diabetes/basic.arff", {}, 442, 11),
        ],
        ids=[
            "test_load_arff_iris",
            "test_load_arff_wine",
            "test_load_arff_diabetes",
        ],
    )
    def test_load_data_from_file(
        self,
        test_datasets_path: pathlib.Path,
        dataset_path: str,
        params: Dict[str, Any],
        nrows: int,
        ncols: int,
    ) -> None:
        super()._test_load_data_from_file(
            dataset_path=test_datasets_path / self.data_type_name / dataset_path,
            params=params,
            nrows=nrows,
            ncols=ncols,
        )

    @pytest.mark.parametrize(
        (
            "dataset_path",
            "params",
            "train_nrows",
            "test_nrows",
            "val_nrows",
            "ncols",
        ),
        [
            ("iris/split.zip", {}, 50, 50, 50, 5),
            ("wine/split.zip", {}, 60, 60, 60, 14),
            ("diabetes/split.zip", {}, 148, 148, 148, 11),
        ],
        ids=[
            "test_load_arff_iris_from_split_zip",
            "test_load_arff_wine_from_split_zip",
            "test_load_arff_diabetes_from_split_zip",
        ],
    )
    def test_load_data_from_zip(
        self,
        test_datasets_path: pathlib.Path,
        dataset_path: str,
        params: Dict[str, Any],
        train_nrows: int,
        test_nrows: int,
        val_nrows: int,
        ncols: int,
    ):
        super()._test_load_data_from_zip(
            dataset_path=test_datasets_path / self.data_type_name / dataset_path,
            params=params,
            train_nrows=train_nrows,
            test_nrows=test_nrows,
            val_nrows=val_nrows,
            ncols=ncols,
        )

    @pytest.mark.parametrize(
        ("dataset_path", "params"),
        [
            ("iris/bad_format.arff", {}),
            ("wine/bad_format.arff", {}),
            ("diabetes/bad_format.arff", {}),
        ],
        ids=[
            "test_load_arff_iris_with_bad_format",
            "test_load_arff_wine_with_bad_format",
            "test_load_arff_diabetes_with_bad_format",
        ],
    )
    def test_dataloader_try_to_load_a_invalid_datasets(
        self,
        test_datasets_path: pathlib.Path,
        dataset_path: str,
        params: Dict[str, Any],
    ):
        super()._test_dataloader_try_to_load_a_invalid_datasets(
            dataset_path=test_datasets_path / self.data_type_name / dataset_path,
            params=params,
        )


# ---------------------------------------------------------------------------
# Native-type extraction tests
# ---------------------------------------------------------------------------


MIXED_ARFF = """@relation mixed

@attribute age NUMERIC
@attribute height REAL
@attribute count INTEGER
@attribute color {red, green, blue}

@data
25,1.75,3,red
30,1.80,5,green
22,1.60,1,blue
"""


def test_arff_supports_native_types_flag():
    """The ARFF loader declares it can expose native types."""
    assert ARFFDataLoader.SUPPORTS_NATIVE_TYPES is True
    assert ARFFDataLoader.get_metadata().get("supports_native_types") is True


def test_arff_extract_native_types_returns_full_schema(tmp_path: pathlib.Path):
    """All standard ARFF attribute kinds map to the expected DashAI types."""
    arff_path = tmp_path / "mixed.arff"
    arff_path.write_text(MIXED_ARFF)

    native_types = ARFFDataLoader().extract_native_types(str(arff_path), {})

    assert set(native_types.keys()) == {
        "age",
        "height",
        "count",
        "color",
    }

    # NUMERIC / REAL / INTEGER → Float / Float / Integer
    assert native_types["age"]["type"] == "Float"
    assert native_types["age"]["dtype"] == "float64"
    assert native_types["height"]["type"] == "Float"
    # scipy reports INTEGER as "numeric" but our mapping accepts both — assert
    # we get a numeric type (Float or Integer) without locking to scipy's quirk.
    assert native_types["count"]["type"] in {"Integer", "Float"}

    # NOMINAL → Categorical with categories from the header
    color = native_types["color"]
    assert color["type"] == "Categorical"
    assert color["encoder"] == "one_hot"
    assert sorted(color["categories"]) == ["blue", "green", "red"]

    # Each column carries an inference_reason that flags arff_metadata as source
    for col_info in native_types.values():
        assert col_info["inference_reason"]["source"] == "arff_metadata"


def test_arff_extract_native_types_shape_matches_ptype(tmp_path: pathlib.Path):
    """Native-type dict has the same keys DashAIPtype would produce."""
    from DashAI.back.types.inf.inference_methods import DashAIPtype

    arff_path = tmp_path / "mixed.arff"
    arff_path.write_text(MIXED_ARFF)

    native_types = ARFFDataLoader().extract_native_types(str(arff_path), {})
    arff_df = ARFFDataLoader()._read_arff_file(str(arff_path))
    ptype_types = DashAIPtype().infer_types(arff_df)

    # Both dicts cover the same columns
    assert set(native_types.keys()) == set(ptype_types.keys())

    # The minimal set of keys consumed downstream by transform_dataset_with_schema
    # is present in every column on both sides.
    required_keys = {"type", "dtype"}
    for col in native_types:
        assert required_keys.issubset(native_types[col].keys())
        assert required_keys.issubset(ptype_types[col].keys())

    # Categorical entries must carry categories + encoder on both sides.
    if native_types["color"]["type"] == "Categorical":
        assert "categories" in native_types["color"]
        assert "encoder" in native_types["color"]


def test_base_dataloader_default_extract_native_types_is_none():
    """Loaders that don't override return None — preserving today's path."""
    from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader

    assert CSVDataLoader.SUPPORTS_NATIVE_TYPES is False
    assert CSVDataLoader.get_metadata().get("supports_native_types") is False
    # extract_native_types may legitimately be called by callers that don't
    # gate on the flag; it must safely return None.
    assert CSVDataLoader().extract_native_types("/nonexistent", {}) is None
