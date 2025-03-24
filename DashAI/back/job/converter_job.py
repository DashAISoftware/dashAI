import logging
import os
import re
from importlib import import_module
from typing import Dict, List

import pandas as pd
from datasets import Dataset
from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.api.api_v1.endpoints.converters import ConverterParams
from DashAI.DashAI.back.converters.scikit_learn.converter_chain import ConverterChain
from DashAI.back.dataloaders.classes.dashai_dataset import (
    load_dataset,
    save_dataset,
    to_dashai_dataset,
)
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
        converter_list_id = self.kwargs["converter_list_id"]
        db = self.kwargs["db"]

        converter_list = db.get(ConverterList, converter_list_id)
        if converter_list is None:
            raise JobError(f"Converter list with id {converter_list_id} does not exist in DB.")

        try:
            converter_list.set_status_as_delivered()
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError("Error setting converter list status as delivered") from e

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
            try:
                module = import_module(module_path)
                converter_constructor = getattr(module, converter_name)
            except ImportError as e:
                log.exception(e)
                raise JobError(f"Error importing converter {converter_name}: {e}") from e

            # Get parameters or empty dict if none
            converter_parameters = converter_params.get("params", {})

            return converter_constructor(**converter_parameters)

        def instantiate_chain(
            steps: List,
            camel_to_snake: re.Pattern,
            converter_submodule_inverse_index: Dict,
        ) -> ConverterChain:
            converter_instances = []

            for converter_name, converter_params in steps:
                converter_instance = instantiate_converters(
                    converter_name,
                    converter_params,
                    camel_to_snake,
                    converter_submodule_inverse_index,
                )
                converter_instances.append(converter_instance)

            return ConverterChain(steps=converter_instances)

        # Extract job parameters
        converter_list_id = self.kwargs["converter_list_id"]
        target_column_index = self.kwargs["target_column_index"]
        db = self.kwargs["db"]

        # Validate input parameters
        try:
            if converter_list_id is None or target_column_index is None:
                raise JobError("Converter list ID and target column index are required")

            converter_list = db.get(ConverterList, converter_list_id)
            if not converter_list:
                raise JobError(f"Converter list with id {converter_list_id} not found")

            converter_list.set_status_as_started()
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError("Error loading converter list info") from e

        # Get dataset
        try:
            dataset_id = converter_list.dataset_id
            dataset = db.get(DatasetModel, dataset_id)

            if not dataset:
                raise JobError(f"Dataset with id {dataset_id} not found")

        except exc.SQLAlchemyError as e:
            log.exception(e)
            converter_list.set_status_as_error()
            db.commit()
            raise JobError("Error loading dataset info") from e

        # Load dataset
        try:
            dataset_path = f"{dataset.file_path}/dataset"
            loaded_dataset = load_dataset(dataset_path)

            # Validate target column index
            if int(target_column_index) < 1 or int(target_column_index) > len(loaded_dataset.features):
                raise JobError(f"Target column index {target_column_index} is out of bounds")

        except Exception as e:
            log.exception(e)
            converter_list.set_status_as_error()
            db.commit()
            raise JobError(f"Cannot load dataset from {dataset_path}") from e

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

            # Build converter name to submodule mapping
            converter_submodule_inverse_index = {}
            for submodule in existing_submodules:
                existing_converters = os.listdir(f"DashAI/back/converters/{submodule}")
                for file in existing_converters:
                    if file.endswith(".py"):
                        converter_name = file[:-3]
                        converter_submodule_inverse_index[converter_name] = submodule

            # Get stored converter configurations
            converters_stored_info = converter_list.converters
            dataset_original_columns = loaded_dataset.column_names

            # Sort converters by order
            converters_sorted_list = sorted(
                converters_stored_info.items(), 
                key=lambda x: x[1]["order"]
            )

            # Process converters
            i = 0
            converter_instances = []

            while i < len(converters_sorted_list):
                converter_name = converters_sorted_list[i][0]
                converter_params = converters_sorted_list[i][1]

                # Check if it's a chain of converters
                if converter_name == "ConverterChain":
                    try:
                        n_steps = int(converter_params["params"]["steps"])

                        # Get the steps
                        chain_steps = converters_sorted_list[i+1:i+n_steps+1]

                        # Instantiate chain of converters
                        chain_instance = instantiate_chain(
                            chain_steps,
                            camel_to_snake,
                            converter_submodule_inverse_index,
                        )

                        # Get scope or use default
                        scope = converter_params.get("scope", {"columns": [], "rows": []})

                        # Add converter chain to instances
                        converter_instances.append({
                            "name": "ConverterChain",
                            "instance": chain_instance,
                            "scope": scope
                        })
                        i += n_steps + 1
                    except Exception as e:
                        log.exception(e)
                        raise JobError(f"Error instantiating converter chain: {e}") from e

                else:
                    # Regular converter
                    converter_instance = instantiate_converters(
                        converter_name,
                        converter_params,
                        camel_to_snake,
                        converter_submodule_inverse_index,
                    )

                    # Get scope or use default
                    scope = converter_params.get("scope", {"columns": [], "rows": []})

                    # Add to instances
                    converter_instances.append({
                        "name": converter_name,
                        "instance": converter_instance,
                        "scope": scope
                    })
                    i += 1

            # Apply each converter in sequence
            for converter_info in converter_instances:
                # Convert dataset to pandas DataFrame
                df_full = loaded_dataset.to_pandas()

                converter = converter_info["instance"]
                converter_scope = converter_info["scope"]

                # Process columns scope
                columns_scope = [column - 1 for column in converter_scope["columns"]]
                scope_column_indexes = sorted(set(columns_scope))

                # If no columns specified, use all columns
                if not scope_column_indexes:
                    scope_column_indexes = list(range(len(loaded_dataset.features)))

                scope_column_names = [
                    dataset_original_columns[index] 
                    for index in scope_column_indexes
                ]

                # Process rows scope
                rows_scope = [row - 1 for row in converter_scope["rows"]]
                scope_rows_indexes = sorted(set(rows_scope))

                # If no rows specified, use all rows
                if not scope_rows_indexes:
                    scope_rows_indexes = list(range(len(df_full)))

                # Adjust target column index (0-based internally)
                target_column_index_0based = int(target_column_index) - 1
                target_column_name = dataset_original_columns[target_column_index_0based]

                # Fit converter
                X = df_full[scope_column_names].iloc[scope_rows_indexes]
                if len(X.shape) == 1:
                    X = X.to_frame()

                y = df_full[target_column_name].iloc[scope_rows_indexes]
                try:
                    converter = converter.fit(X, y)
                except Exception as e:
                    log.exception(e)
                    raise JobError(f"Error fitting converter {converter_name}: {e}") from e

                # Transform data
                X = df_full[scope_column_names]
                y = df_full[target_column_name]

                if len(X.shape) == 1:
                    X = X.to_frame()

                try:
                    resulting_dataframe = converter.transform(X, y)
                except Exception as e:
                    log.exception(e)
                    raise JobError(f"Error transforming data: {e}") from e

                # Update dataframe
                columns_to_drop = df_full.columns[scope_column_indexes]
                df_full.drop(columns=columns_to_drop, axis=1, inplace=True)

                # Insert transformed columns at their original positions
                for i, column in enumerate(resulting_dataframe.columns):
                    if i < len(scope_column_indexes):
                        df_full.insert(
                            scope_column_indexes[i], 
                            column, 
                            resulting_dataframe[column]
                        )

                # Add any additional columns created by the transformer
                if len(resulting_dataframe.columns) > len(scope_column_indexes):
                    # Get the new columns
                    remaining_columns = resulting_dataframe.columns[len(scope_column_indexes):]

                    # Create DataFrame with just these columns
                    remaining_df = resulting_dataframe[remaining_columns].copy()

                    # Ensure index alignment
                    remaining_df.index = df_full.index

                    # Concatenate with the main DataFrame
                    df_full = pd.concat([df_full, remaining_df], axis=1)

                # Create updated DashAI dataset
                loaded_dataset = to_dashai_dataset(Dataset.from_pandas(df_full))

            # Save the final dataset
            save_dataset(loaded_dataset, f"{dataset_path}")
            converter_list.set_status_as_finished()
            db.commit()
            db.refresh(dataset)

        except Exception as e:
            log.exception(e)
            converter_list.set_status_as_error()
            db.commit()
            raise JobError(f"Error applying converters to dataset {dataset_id}: {e}") from e