"""Arrow IPC DataLoader tests module."""

import pathlib
from typing import Any, Dict

import pytest
from sklearn.datasets import load_diabetes, load_iris, load_wine

from DashAI.back.dataloaders.classes.arrow_dataloader import ArrowDataLoader
from tests.back.dataloaders.base_tabular_dataloader_tests import (
    BaseTabularDataLoaderTester,
)
from tests.back.test_datasets_generator import ArrowTestDatasetGenerator


@pytest.fixture(scope="module", autouse=True)
def _setup(test_datasets_path: pathlib.Path, random_state: int) -> None:
    """Generate the Arrow IPC test datasets."""
    df_iris = load_iris(return_X_y=False, as_frame=True)["frame"]  # type: ignore
    df_wine = load_wine(return_X_y=False, as_frame=True)["frame"]  # type: ignore
    df_diabetes = load_diabetes(return_X_y=False, as_frame=True)["frame"]  # type: ignore

    for df, name in [(df_iris, "iris"), (df_wine, "wine"), (df_diabetes, "diabetes")]:
        ArrowTestDatasetGenerator(
            df=df,
            dataset_name=name,
            ouptut_path=test_datasets_path,
            random_state=random_state,
        )


class TestArrowDataloader(BaseTabularDataLoaderTester):
    @property
    def dataloader_cls(self):
        return ArrowDataLoader

    @property
    def data_type_name(self):
        return "arrow"

    @pytest.mark.parametrize(
        ("dataset_path", "params", "nrows", "ncols"),
        [
            ("iris/basic.arrow", {}, 150, 5),
            ("wine/basic.arrow", {}, 178, 14),
            ("diabetes/basic.arrow", {}, 442, 11),
        ],
        ids=[
            "test_load_arrow_iris",
            "test_load_arrow_wine",
            "test_load_arrow_diabetes",
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
            "test_load_arrow_iris_from_split_zip",
            "test_load_arrow_wine_from_split_zip",
            "test_load_arrow_diabetes_from_split_zip",
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
            ("iris/bad_format.arrow", {}),
            ("wine/bad_format.arrow", {}),
            ("diabetes/bad_format.arrow", {}),
        ],
        ids=[
            "test_load_arrow_iris_with_bad_format",
            "test_load_arrow_wine_with_bad_format",
            "test_load_arrow_diabetes_with_bad_format",
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

    @pytest.mark.parametrize(
        ("dataset_path", "params", "nrows", "ncols"),
        [
            ("iris/flat.zip", {}, 150, 5),
            ("wine/flat.zip", {}, 178, 14),
            ("diabetes/flat.zip", {}, 442, 11),
        ],
        ids=[
            "test_load_arrow_iris_from_flat_zip",
            "test_load_arrow_wine_from_flat_zip",
            "test_load_arrow_diabetes_from_flat_zip",
        ],
    )
    def test_load_data_from_flat_zip(
        self,
        test_datasets_path: pathlib.Path,
        dataset_path: str,
        params: Dict[str, Any],
        nrows: int,
        ncols: int,
    ):
        loader = self.dataloader_cls()
        dataset = loader.load_data(
            filepath_or_buffer=str(
                test_datasets_path / self.data_type_name / dataset_path
            ),
            temp_path="tests/back/dataloaders",
            params=params,
        )
        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        assert isinstance(dataset, DashAIDataset)
        assert dataset.num_rows == nrows
        assert dataset.num_columns == ncols
