"""DashAI CSV Type Inference Dataloader."""

import os
import shutil
import re
import json
import logging
from typing import Any, Dict, List, Set, Tuple, Union
from collections import Counter
from pathlib import Path

from beartype import beartype
from datasets import DatasetDict, load_dataset, Features, Value, Image
from starlette.datastructures import UploadFile
from PIL import Image as PILImage

from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader, CSVDataloaderSchema
from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset, DashAIDataset

# Get the directory of the current file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logger
logger = logging.getLogger(__name__)

class CSVTypeInferenceDataLoader(CSVDataLoader):
    """Data loader for tabular data in CSV files with automatic type inference and image detection."""

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = CSVDataloaderSchema  # Usamos el mismo esquema que CSVDataLoader
    DESCRIPTION = "A dataloader that automatically infers column types from CSV files and detects image columns"
    
    # Common image file extensions
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico', '.heic', '.heif'
    }
    
    # Threshold for determining if a column contains images (percentage of values that look like image paths)
    IMAGE_THRESHOLD = 0.8
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("Initialized CSVTypeInferenceDataLoader")
    
    def _is_image_path(self, value: str) -> bool:
        """Check if a string value looks like an image path based on file extension.
        
        Parameters
        ----------
        value : str
            The string value to check
            
        Returns
        -------
        bool
            True if the string appears to be an image path, False otherwise
        """
        if not isinstance(value, str):
            return False
            
        # Extract file extension using regex to handle various path formats
        extension_match = re.search(r'(\.[a-zA-Z0-9]+)$', value.lower())
        if not extension_match:
            return False
            
        extension = extension_match.group(1)
        is_image = extension in self.IMAGE_EXTENSIONS
            
        return is_image
    
    def _check_image_exists(self, image_path: str) -> bool:
        """Check if an image file exists and can be opened.
        
        Parameters
        ----------
        image_path : str
            Path to the image file
            
        Returns
        -------
        bool
            True if the image exists and can be opened, False otherwise
        """
        try:
            # Try to open the image with PIL to verify it's a valid image
            with PILImage.open(image_path) as img:
                # Just accessing a property to verify the image is valid
                _ = img.size
            return True
        except Exception:
            return False
    
    def _verify_image_paths(self, column_values: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """Verify which image paths exist and can be loaded.
        
        Parameters
        ----------
        column_values : List[str]
            List of string values that are potential image paths
            
        Returns
        -------
        Tuple[List[str], List[str], List[str]]
            A tuple containing (valid_paths, invalid_paths, not_image_paths)
        """
        valid_paths = []
        invalid_paths = []
        not_image_paths = []
        
        for value in column_values:
            if value is None:
                continue
                
            if not self._is_image_path(value):
                not_image_paths.append(value)
                continue
                
            if self._check_image_exists(value):
                valid_paths.append(value)
            else:
                invalid_paths.append(value)
        
        return valid_paths, invalid_paths, not_image_paths
    
    def _analyze_string_column(self, column_values: List[str]) -> Tuple[bool, float, Dict[str, Any]]:
        """Analyze a string column to determine if it contains image paths.
        
        Parameters
        ----------
        column_values : List[str]
            List of string values in the column
            
        Returns
        -------
        Tuple[bool, float, Dict[str, Any]]
            A tuple containing (is_image_column, image_percentage, stats)
        """
        # Verify which paths exist and can be loaded
        valid_paths, invalid_paths, not_image_paths = self._verify_image_paths(column_values)
        
        # Calculate statistics
        total_values = len(column_values)
        image_paths_count = len(valid_paths) + len(invalid_paths)
        image_percentage = (image_paths_count / total_values) * 100 if total_values > 0 else 0
        valid_percentage = (len(valid_paths) / image_paths_count) * 100 if image_paths_count > 0 else 0
        
        # Determine if this is an image column based on the percentage of image paths
        is_image_column = image_percentage / 100 >= self.IMAGE_THRESHOLD
        
        # Return the results
        stats = {
            "image_paths_count": image_paths_count,
            "image_percentage": image_percentage,
            "valid_paths_count": len(valid_paths),
            "invalid_paths_count": len(invalid_paths),
            "valid_percentage": valid_percentage,
            "valid_paths": valid_paths,
            "invalid_paths": invalid_paths
        }
        
        return is_image_column, image_percentage / 100, stats
    
    def _detect_image_columns(self, dataset: DatasetDict) -> Tuple[DatasetDict, Dict[str, Any]]:
        """Detect columns that contain image paths and convert them to Image type.
        
        Parameters
        ----------
        dataset : DatasetDict
            The dataset to analyze
            
        Returns
        -------
        Tuple[DatasetDict, Dict[str, Any]]
            A tuple containing:
            - The dataset with image columns converted to Image type
            - Dictionary with image columns information for JSON output
        """
        # Dictionary to store image column information for JSON output
        image_columns_info = {}
        
        for split in dataset.keys():
            # Dictionary to store image statistics for this split
            split_image_stats = {}
            
            # Analyze string columns to detect image paths
            image_columns = []
            columns_to_convert = {}
            
            for column, dtype in dataset[split].features.items():
                if isinstance(dtype, Value) and dtype.dtype == "string":
                    # Get column values
                    column_values = dataset[split][column]
                    
                    # Check if column contains image paths
                    is_image_column, image_percentage, stats = self._analyze_string_column(column_values)
                    
                    # Store column information for JSON
                    image_columns_info[column] = {
                        "is_image_column": is_image_column,
                        "threshold_used": self.IMAGE_THRESHOLD,
                        "image_percentage": stats['image_percentage'],
                        "total_paths": len(column_values),
                        "image_paths_count": stats['image_paths_count'],
                        "valid_paths_count": stats['valid_paths_count'],
                        "invalid_paths_count": stats['invalid_paths_count'],
                        "invalid_paths": stats['invalid_paths'],
                        "valid_paths": stats['valid_paths']
                    }
                    
                    if is_image_column:
                        image_columns.append(column)
                        # Store image statistics for this column
                        split_image_stats[column] = stats
                        
                        # If there are no invalid images, mark this column for conversion
                        if stats['invalid_paths_count'] == 0 and stats['valid_paths_count'] > 0:
                            columns_to_convert[column] = True
            
            # Convert valid columns to Image type.
            if columns_to_convert:
                # Create a new Features with the converted image columns
                new_features = dict(dataset[split].features)
                for column in columns_to_convert:
                    new_features[column] = Image()
                
                # Apply the new features to the dataset
                dataset[split] = dataset[split].cast(Features(new_features))
        
        # Add image columns info to dataset metadata
        if not hasattr(dataset, 'info'):
            dataset.info = {}
        dataset.info['image_columns'] = image_columns
        dataset.info['image_columns_info'] = image_columns_info
        
        return dataset, image_columns_info

    @beartype
    def load_data(
        self,
        filepath_or_buffer: Union[UploadFile, str],
        temp_path: str,
        params: Dict[str, Any],
    ) -> Union[DatasetDict, DashAIDataset]:
        """Load the uploaded CSV files into a dataset with automatic type inference and image detection.

        Parameters
        ----------
        filepath_or_buffer : Union[UploadFile, str], optional
            An URL where the dataset is located or a FastAPI/Uvicorn uploaded file
            object.
        temp_path : str
            The temporary path where the files will be extracted and then uploaded.
        params : Dict[str, Any]
            Dict with the dataloader parameters. The options are:
            - `separator` (str): The character that delimits the CSV data.

        Returns
        -------
        Union[DatasetDict, DashAIDataset]
            A dataset with the loaded data, inferred types, and detected image columns.
            Returns a DashAIDataset to ensure compatibility with save_dataset function.
        """
        # Use the _check_params method from CSVDataLoader
        self._check_params(params)
        separator = params["separator"]

        if isinstance(filepath_or_buffer, str):
            dataset = load_dataset(
                "csv",
                data_files=filepath_or_buffer,
                sep=separator,
            )
        elif isinstance(filepath_or_buffer, UploadFile):
            files_path = self.extract_files(
                temp_path,
                filepath_or_buffer,
            )
            
            if files_path.split("/")[-1] == "files":
                try:
                    dataset = load_dataset(
                        "csv",
                        data_dir=files_path,
                        sep=separator,
                    )
                finally:
                    shutil.rmtree(temp_path, ignore_errors=True)
            else:
                try:
                    dataset = load_dataset(
                        "csv",
                        data_files=files_path,
                        sep=separator,
                    )
                finally:
                    os.remove(files_path)
        
        # Process the dataset to detect image columns
        processed_dataset, image_columns_info = self._detect_image_columns(dataset)
        
        # Store the image columns info directly as an attribute of the dataset
        processed_dataset.image_columns_info = image_columns_info
        
        # Save a copy of the image columns info
        debug_json_path = os.path.join(temp_path, "image_columns_info.json")
        try:
            with open(debug_json_path, "w", encoding="utf-8") as f:
                json.dump(image_columns_info, f, indent=2)
        except Exception:
            pass
        
        # Convert to DashAIDataset before returning
        dashai_dataset = to_dashai_dataset(processed_dataset)
        
        # Ensure image_columns_info is preserved in the conversion
        if hasattr(processed_dataset, 'image_columns_info'):
            dashai_dataset.image_columns_info = processed_dataset.image_columns_info
        
        return dashai_dataset 