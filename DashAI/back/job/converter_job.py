import logging
import os
import re
from importlib import import_module
from typing import Dict, List, Union

import pandas as pd
from datasets import Dataset, DatasetDict
from datasets import Dataset, DatasetDict
from kink import inject
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import exc
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.api.api_v1.endpoints.converters import ConverterParams
from DashAI.back.converters.scikit_learn.pipeline import Pipeline
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    load_dataset,
    save_dataset,
    to_dashai_dataset,
)
from DashAI.back.dependencies.database.models import ConverterList
from DashAI.back.dependencies.database.models import Dataset as DatasetModel
from DashAI.back.dependencies.database.models import ConverterList
from DashAI.back.dependencies.database.models import Dataset as DatasetModel
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ConverterListJob(BaseJob):
    """ConverterListJob class to modify a dataset by applying a sequence of converters."""

    def set_status_as_delivered(self) -> None:
        """Set the status of the list as delivered."""
        converter_list_id: int = self.kwargs["converter_list_id"]
        db: Session = self.kwargs["db"]
        converter_list: ConverterList = db.get(ConverterList, converter_list_id)
        if converter_list is None:
            raise JobError(
                f"Converter list with id {converter_list_id} does not exist in DB."
            )
        try:
            converter_list.set_status_as_delivered()
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError(
                "Error while setting the status of the converter list as delivered."
            ) from e

    @inject
    def run(
        self,
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
    ) -> None:

        def instantiate_converters(
            converter_name: str,
            converter_params: ConverterParams,
            camel_to_snake: re.Pattern,
            converter_submodule_inverse_index: Dict,
        ) -> object:
            # Get converter constructor and parameters
            converter_filename = camel_to_snake.sub("_", converter_name).lower()
            submodule = converter_submodule_inverse_index[converter_filename]
            module_path = f"DashAI.back.converters.{submodule}.{converter_filename}"

            # Import the converter
            module = import_module(module_path)
            converter_constructor = getattr(module, converter_name)
            converter_parameters = (
                converter_params["params"]
                if "params" in converter_params.keys()
                else {}
            )

            return converter_constructor(**converter_parameters)

        def instantiate_pipeline(
            steps: List,
            camel_to_snake: re.Pattern,
            converter_submodule_inverse_index: Dict,
        ) -> Pipeline:
            converter_instances = []
            for converter_name, converter_params in steps:
                converter_instance = instantiate_converters(
                    converter_name,
                    converter_params,
                    camel_to_snake,
                    converter_submodule_inverse_index,
                )
                converter_instances.append(converter_instance)

            return Pipeline(steps=converter_instances)

        converter_list_id: int = self.kwargs["converter_list_id"]
        target_column_index: int = self.kwargs["target_column_index"]
        db: Session = self.kwargs["db"]

        # Load the converter list information
        try:
            if converter_list_id is None or target_column_index is None:
                raise JobError(
                    "Converter list ID and target column index are required to run the job."
                )

            converter_list: ConverterList = db.get(ConverterList, converter_list_id)
            if not converter_list:
                raise JobError(
                    f"Converter list with id {converter_list_id} does not exist in DB."
                )

            converter_list.set_status_as_started()
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError("Error while loading the converter list info.") from e

        # Load dataset information
        try:
            dataset_id = converter_list.dataset_id
            dataset: DatasetModel = db.get(DatasetModel, dataset_id)
            if not dataset:
                raise JobError(f"Dataset with id {dataset_id} does not exist in DB.")
        except exc.SQLAlchemyError as e:
            log.exception(e)
            converter_list.set_status_as_error()
            db.commit()
            raise JobError("Error while loading the dataset info.") from e

        # Load dataset
        try:
            dataset_path = f"{dataset.file_path}/dataset"
            dataset_dict = load_dataset(dataset_path, keep_in_memory=True)
            dataset_dict = load_dataset(dataset_path, keep_in_memory=True)
            if int(target_column_index) < 1 or int(target_column_index) > len(
                dataset_dict["train"].features
            ):
                raise JobError(
                    f"Target column index {target_column_index} is out of bounds."
                )
        except Exception as e:
            log.exception(e)
            converter_list.set_status_as_error()
            db.commit()
            raise JobError(f"Can not load dataset from path {dataset_path}") from e

        try:
            # Regex to convert camel case to snake case
            camel_to_snake = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

            # Create a dictionary with the submodule for each converter
            converters_list_dir = os.listdir("DashAI/back/converters")
            existing_submodules = [
                submodule
                for submodule in converters_list_dir
                if os.path.isdir(f"DashAI/back/converters/{submodule}")
            ]
            converter_submodule_inverse_index = {}
            for submodule in existing_submodules:
                existing_converters = os.listdir(f"DashAI/back/converters/{submodule}")
                for file in existing_converters:
                    if file.endswith(".py"):
                        converter_name = file[:-3]
                        converter_submodule_inverse_index[converter_name] = submodule

            converters_stored_info: Dict[str, ConverterParams] = (
                converter_list.converters
            )
            dataset_original_columns = dataset_dict["train"].column_names

            # Pairs of converter name and converter params
            # (order, hyperparameters and scope) sorted by order
            converters_sorted_list = sorted(
                converters_stored_info.items(), key=lambda x: x[1]["order"]
            )

            i = 0
            converter_instances = []
            while i < len(converters_sorted_list):
                converter_name = converters_sorted_list[i][0]
                converter_params = converters_sorted_list[i][1]
                if converter_name == "Pipeline":
                    n_steps = int(converter_params["params"]["steps"])
                    # Instantiate the following n_steps converters and add them to the pipeline
                    pipeline_instance = instantiate_pipeline(
                        converters_sorted_list[i + 1 : i + n_steps + 1],
                        camel_to_snake,
                        converter_submodule_inverse_index,
                    )
                    # Add the pipeline to the list of converters
                    converter_instances.append(
                        {
                            "name": "Pipeline",
                            "instance": pipeline_instance,
                            "scope": (
                                converter_params["scope"]
                                if "scope" in converter_params.keys()
                                else {"columns": [], "rows": []}
                            ),
                        }
                    )
                    i += n_steps + 1
                else:
                    # Instantiate the converter and add it to the list of converters
                    converter_instance = instantiate_converters(
                        converter_name,
                        converter_params,
                        camel_to_snake,
                        converter_submodule_inverse_index,
                    )
                    converter_instances.append(
                        {
                            "name": converter_name,
                            "instance": converter_instance,
                            "scope": (
                                converter_params["scope"]
                                if "scope" in converter_params.keys()
                                else {"columns": [], "rows": []}
                            ),
                        }
                    )
                    i += 1

            for converter_info in converter_instances:
                dataset_train: DashAIDataset = dataset_dict["train"]
                df_train = dataset_train.to_pandas()
                dataset_test: DashAIDataset = dataset_dict["test"]
                df_test = dataset_test.to_pandas()
                dataset_validation: DashAIDataset = dataset_dict["validation"]
                df_validation = dataset_validation.to_pandas()
                df_concatenated = pd.concat([df_train, df_test, df_validation], axis=0)

                converter = converter_info["instance"]
                converter_scope = converter_info["scope"]

                # Process columns scope
                columns_scope = [column - 1 for column in converter_scope["columns"]]
                scope_column_indexes = list(set(columns_scope))
                scope_column_indexes.sort()
                if scope_column_indexes == []:
                    scope_column_indexes = list(range(len(dataset_train.features)))
                scope_column_names = [
                    dataset_original_columns[index] for index in scope_column_indexes
                ]

                # Process rows scope
                rows_scope = [row - 1 for row in converter_scope["rows"]]
                scope_rows_indexes = list(set(rows_scope))
                scope_rows_indexes.sort()
                if scope_rows_indexes == []:
                    scope_rows_indexes = list(range(len(df_concatenated)))

                target_column_index = int(target_column_index) - 1
                target_column_name = dataset_original_columns[target_column_index]

                # Fit converter
                X = df_concatenated[scope_column_names].iloc[scope_rows_indexes]
                if len(X.shape) == 1:
                    X = X.to_frame()
                y = df_concatenated[target_column_name].iloc[scope_rows_indexes]
                converter = converter.fit(X, y)

                # Transform data
                X = df_concatenated[scope_column_names]
                y = df_concatenated[target_column_name]
                if len(X.shape) == 1:
                    X = X.to_frame()
                resulting_dataframe = converter.transform(X, y)

                # Update dataframe
                columns_to_drop = df_concatenated.columns[scope_column_indexes]
                df_concatenated.drop(columns_to_drop, axis=1, inplace=True)
                
                # Insert the resulting dataframe columns that have corresponding positions
                for i, column in enumerate(resulting_dataframe.columns):
                    if i < len(scope_column_indexes):
                        df_concatenated.insert(
                            scope_column_indexes[i], column, resulting_dataframe[column]
                        )

                # Once we've inserted all columns that have positions, concatenate any remaining columns
                if len(resulting_dataframe.columns) > len(scope_column_indexes):
                    remaining_columns = resulting_dataframe.columns[len(scope_column_indexes):]
                    # Create a DataFrame with just the remaining columns
                    remaining_df = resulting_dataframe[remaining_columns].copy()
                    # Reset the index to ensure it's unique before concatenating
                    # or use the index from df_concatenated to ensure alignment
                    remaining_df.index = df_concatenated.index
                    # Now concatenate with the fixed index
                    df_concatenated = pd.concat([df_concatenated, remaining_df], axis=1)
                

                # Update splits
                df_train = df_concatenated.iloc[: len(dataset_train)]
                df_test = df_concatenated.iloc[
                    len(dataset_train) : len(dataset_train) + len(dataset_test)
                ]
                df_validation = df_concatenated.iloc[
                    len(dataset_train) + len(dataset_test) :
                ]

                # Create final dataset
                dataset_dict = DatasetDict(
                    {
                        "train": Dataset.from_pandas(df_train, preserve_index=False),
                        "test": Dataset.from_pandas(df_test, preserve_index=False),
                        "validation": Dataset.from_pandas(
                            df_validation, preserve_index=False
                        ),
                    }
                )
                dataset_dict = to_dashai_dataset(dataset_dict)

            # Save the final dataset
            save_dataset(dataset_dict, f"{dataset_path}")
            converter_list.set_status_as_finished()
            db.commit()
            db.refresh(dataset)

        except Exception as e:
            log.exception(e)
            converter_list.set_status_as_error()
            db.commit()
            raise JobError(
                f"Error while applying converters to dataset with id {dataset_id}. Error: {e}"
            ) from e
