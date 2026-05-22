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
