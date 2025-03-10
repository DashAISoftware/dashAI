"""DashAI CSV Type Inference Dataloader."""

import os
import shutil
import re
import logging
import json
from typing import Any, Dict, List, Set, Tuple, Union
from collections import Counter
from pathlib import Path

from beartype import beartype
from datasets import DatasetDict, load_dataset, Features, Value, Image
from starlette.datastructures import UploadFile
from PIL import Image as PILImage

from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader, CSVDataloaderSchema

# Get the directory of the current file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(CURRENT_DIR, "csv_inference_debug.log")

# Direct print for immediate visibility (these will show up regardless of logging configuration)
print(f"\n\n{'='*80}")
print(f"CSV TYPE INFERENCE DATALOADER INITIALIZING")
print(f"Debug log will be written to: {LOG_FILE}")
print(f"{'='*80}\n\n")

# Configure logging to write to a file in the same directory
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Standard output
        logging.FileHandler(LOG_FILE)  # File in the same directory
    ]
)
logger = logging.getLogger("CSVTypeInferenceDataLoader")

# Write a test message to verify logging is working
logger.info(f"CSVTypeInferenceDataLoader initialized - logging to {LOG_FILE}")

# Write directly to the log file as a backup method
with open(LOG_FILE, "a") as f:
    f.write("\n\n" + "="*80 + "\n")
    f.write("DIRECT WRITE: CSV TYPE INFERENCE DATALOADER INITIALIZED\n")
    f.write("="*80 + "\n\n")

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
        # Direct print when an instance is created
        print(f"CSVTypeInferenceDataLoader instance created")
        # Also log to file directly
        with open(LOG_FILE, "a") as f:
            f.write(f"CSVTypeInferenceDataLoader instance created at {import_time}\n")
        # Log through the logger
        logger.info("CSVTypeInferenceDataLoader instance created")
    
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
        
        # Debug print for individual values (commented out to avoid excessive logging)
        # if is_image:
        #     logger.debug(f"Detected image path: {value} with extension {extension}")
            
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
        except Exception as e:
            # Log the error but don't raise it
            logger.debug(f"Could not open image {image_path}: {str(e)}")
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
        # Count how many values look like image paths
        image_paths_count = 0
        sample_image_paths = []
        
        # Verify which paths exist and can be loaded
        valid_paths, invalid_paths, not_image_paths = self._verify_image_paths(column_values)
        
        # Calculate statistics
        total_values = len(column_values)
        image_paths_count = len(valid_paths) + len(invalid_paths)
        image_percentage = (image_paths_count / total_values) * 100 if total_values > 0 else 0
        valid_percentage = (len(valid_paths) / image_paths_count) * 100 if image_paths_count > 0 else 0
        
        # Determine if this is an image column based on the percentage of image paths
        is_image_column = image_percentage / 100 >= self.IMAGE_THRESHOLD
        
        # Collect sample image paths for logging
        sample_image_paths = (valid_paths + invalid_paths)[:5]
        
        # Return the results
        stats = {
            "image_paths_count": image_paths_count,
            "image_percentage": image_percentage,
            "valid_paths_count": len(valid_paths),
            "invalid_paths_count": len(invalid_paths),
            "valid_percentage": valid_percentage,
            "sample_image_paths": sample_image_paths,
            "valid_paths": valid_paths,
            "invalid_paths": invalid_paths
        }
        
        return is_image_column, image_percentage / 100, stats
    
    def _detect_image_columns(self, dataset: DatasetDict) -> DatasetDict:
        """Detect columns that contain image paths and convert them to Image type.
        
        Parameters
        ----------
        dataset : DatasetDict
            The dataset to analyze
            
        Returns
        -------
        DatasetDict
            The dataset with image columns converted to Image type
        """
        logger.info("=== Starting Image Column Detection ===")
        
        # Dictionary to store image column information for JSON output
        image_columns_info = {}
        
        for split in dataset.keys():
            logger.info(f"Analyzing split: '{split}'")
            
            # Dictionary to store image statistics for this split
            split_image_stats = {}
            
            # Analyze string columns to detect image paths
            image_columns = []
            
            for column, dtype in dataset[split].features.items():
                if isinstance(dtype, Value) and dtype.dtype == "string":
                    logger.info(f"Analyzing column: '{column}' (type: {dtype.dtype})")
                    
                    # Get column values
                    column_values = dataset[split][column]
                    
                    # Print a sample of values for debugging
                    logger.info(f"Analyzing {len(column_values)} values in column '{column}'...")
                    
                    # Check if column contains image paths
                    is_image_column, image_percentage, stats = self._analyze_string_column(column_values)
                    
                    # Log the results
                    logger.info(f"Column analysis: {stats['image_paths_count']}/{len(column_values)} values look like image paths ({stats['image_percentage']:.2f}%)")
                    logger.info(f"Is image column: {is_image_column} (threshold: {self.IMAGE_THRESHOLD*100:.2f}%)")
                    print(f"Column analysis: {stats['image_paths_count']}/{len(column_values)} values look like image paths ({stats['image_percentage']:.2f}%)")
                    print(f"Is image column: {is_image_column} (threshold: {self.IMAGE_THRESHOLD*100:.2f}%)")
                    
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
                        logger.info(f"  - {column}")
                    else:
                        if stats['image_paths_count'] > 0:
                            logger.info(f"Sample image paths detected but below threshold: {stats['sample_image_paths']}")
                else:
                    logger.info(f"Skipping column '{column}' (type: {dtype.dtype})")
            
            # Generate a summary report for this split
            if split_image_stats:
                report = "\n=== Image Column Summary Report ===\n\n"
                report += f"Split: '{split}'\n"
                
                for column, stats in split_image_stats.items():
                    report += f"  Column: '{column}'\n"
                    report += f"    - Total image paths: {stats['image_paths_count']}\n"
                    report += f"    - Valid image paths: {stats['valid_paths_count']} ({stats['valid_percentage']:.2f}%)\n"
                    report += f"    - Invalid image paths: {stats['invalid_paths_count']}\n"
                    
                    if stats['invalid_paths']:
                        report += f"    - Sample invalid paths: {stats['invalid_paths'][:3]}\n"
                
                logger.info(report)
                print(report)
        
        # Write the image columns info to a JSON file
        json_path = os.path.join(CURRENT_DIR, "image_columns_info.json")
        with open(json_path, "w") as f:
            json.dump(image_columns_info, f, indent=2)
        logger.info(f"Image columns information saved to: {json_path}")
        
        logger.info("=== Image Column Detection Complete ===")
        
        # Add image columns info to dataset metadata
        if not hasattr(dataset, 'info'):
            dataset.info = {}
        dataset.info['image_columns'] = image_columns
        dataset.info['image_columns_info'] = image_columns_info
        
        return dataset

    @beartype
    def load_data(
        self,
        filepath_or_buffer: Union[UploadFile, str],
        temp_path: str,
        params: Dict[str, Any],
    ) -> DatasetDict:
        """Load the uploaded CSV files into a DatasetDict with automatic type inference and image detection.

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
        DatasetDict
            A HuggingFace's Dataset with the loaded data, inferred types, and detected image columns.
        """
        # Direct print at the start of load_data
        print(f"\n\n{'*'*80}")
        print(f"LOAD_DATA METHOD CALLED")
        print(f"{'*'*80}\n\n")
        
        # Direct write to log file
        with open(LOG_FILE, "a") as f:
            f.write(f"\n\n{'*'*80}\n")
            f.write(f"LOAD_DATA METHOD CALLED\n")
            f.write(f"{'*'*80}\n\n")
        
        # Use the _check_params method from CSVDataLoader
        self._check_params(params)
        separator = params["separator"]

        load_msg = f"=== Loading CSV data with separator: '{separator}' ==="
        print(load_msg)
        logger.info(load_msg)

        if isinstance(filepath_or_buffer, str):
            filepath_msg = f"Loading from filepath: {filepath_or_buffer}"
            print(filepath_msg)
            logger.info(filepath_msg)
            
            try:
                dataset = load_dataset(
                    "csv",
                    data_files=filepath_or_buffer,
                    sep=separator,
                )
                
                success_msg = f"✅ Successfully loaded dataset from filepath: {filepath_or_buffer}"
                print(success_msg)
                logger.info(success_msg)
            except Exception as e:
                error_msg = f"❌ Error loading dataset from filepath: {filepath_or_buffer}"
                error_details = f"Error details: {str(e)}"
                
                print(error_msg)
                print(error_details)
                logger.error(error_msg)
                logger.error(error_details)
                
                # Direct write to log file
                with open(LOG_FILE, "a") as f:
                    f.write(f"{error_msg}\n")
                    f.write(f"{error_details}\n")
                
                raise

        elif isinstance(filepath_or_buffer, UploadFile):
            upload_msg = f"Loading from uploaded file: {filepath_or_buffer.filename} (content type: {filepath_or_buffer.content_type})"
            print(upload_msg)
            logger.info(upload_msg)
            
            files_path = self.extract_files(
                temp_path,
                filepath_or_buffer,
            )
            
            extract_msg = f"Files extracted to: {files_path}"
            print(extract_msg)
            logger.info(extract_msg)
            
            if files_path.split("/")[-1] == "files":
                try:
                    dir_msg = f"Loading from directory: {files_path}"
                    print(dir_msg)
                    logger.info(dir_msg)
                    
                    # List files in directory to verify content
                    dir_files = os.listdir(files_path)
                    
                    files_msg = f"Files in directory: {dir_files}"
                    print(files_msg)
                    logger.info(files_msg)
                    
                    try:
                        dataset = load_dataset(
                            "csv",
                            data_dir=files_path,
                            sep=separator,
                        )
                        
                        success_msg = f"✅ Successfully loaded dataset from directory: {files_path}"
                        print(success_msg)
                        logger.info(success_msg)
                    except Exception as e:
                        error_msg = f"❌ Error loading dataset from directory: {files_path}"
                        error_details = f"Error details: {str(e)}"
                        
                        print(error_msg)
                        print(error_details)
                        logger.error(error_msg)
                        logger.error(error_details)
                        
                        # Direct write to log file
                        with open(LOG_FILE, "a") as f:
                            f.write(f"{error_msg}\n")
                            f.write(f"{error_details}\n")
                        
                        raise
                finally:
                    shutil.rmtree(temp_path, ignore_errors=True)
            else:
                try:
                    file_msg = f"Loading from file: {files_path}"
                    print(file_msg)
                    logger.info(file_msg)
                    
                    # Check if file exists and get its size
                    if os.path.exists(files_path):
                        file_size = os.path.getsize(files_path)
                        
                        size_msg = f"File exists, size: {file_size} bytes"
                        print(size_msg)
                        logger.info(size_msg)
                        
                        # Read first few lines to verify content
                        try:
                            with open(files_path, 'r', encoding='utf-8') as f:
                                first_lines = [next(f) for _ in range(3)]
                            
                            preview_msg = f"First few lines of file:\n{''.join(first_lines)}"
                            print(preview_msg)
                            logger.info(preview_msg)
                        except Exception as e:
                            preview_error = f"Could not read file preview: {str(e)}"
                            print(preview_error)
                            logger.warning(preview_error)
                    else:
                        not_exist_msg = f"File does not exist: {files_path}"
                        print(not_exist_msg)
                        logger.error(not_exist_msg)
                    
                    try:
                        dataset = load_dataset(
                            "csv",
                            data_files=files_path,
                            sep=separator,
                        )
                        
                        success_msg = f"✅ Successfully loaded dataset from file: {files_path}"
                        print(success_msg)
                        logger.info(success_msg)
                    except Exception as e:
                        error_msg = f"❌ Error loading dataset from file: {files_path}"
                        error_details = f"Error details: {str(e)}"
                        
                        print(error_msg)
                        print(error_details)
                        logger.error(error_msg)
                        logger.error(error_details)
                        
                        # Direct write to log file
                        with open(LOG_FILE, "a") as f:
                            f.write(f"{error_msg}\n")
                            f.write(f"{error_details}\n")
                        
                        raise
                finally:
                    os.remove(files_path)

        splits_msg = f"Loaded dataset with splits: {list(dataset.keys())}"
        print(splits_msg)
        logger.info(splits_msg)
        
        for split_name, split_dataset in dataset.items():
            split_info = f"Split '{split_name}' has {len(split_dataset)} rows and {len(split_dataset.features)} columns"
            col_types = f"Column types: {[(name, feature.dtype) for name, feature in split_dataset.features.items()]}"
            
            print(split_info)
            print(col_types)
            logger.info(split_info)
            logger.info(col_types)
        
        # Process the dataset to detect image columns
        detect_msg = "Starting image column detection..."
        print(f"\n{detect_msg}")
        logger.info(detect_msg)
        
        processed_dataset = self._detect_image_columns(dataset)
        
        complete_msg = "LOAD_DATA METHOD COMPLETED SUCCESSFULLY"
        print(f"\n\n{'*'*80}")
        print(complete_msg)
        print(f"{'*'*80}\n\n")
        
        # Direct write to log file
        with open(LOG_FILE, "a") as f:
            f.write(f"\n\n{'*'*80}\n")
            f.write(f"{complete_msg}\n")
            f.write(f"{'*'*80}\n\n")
        
        return processed_dataset

# Add a timestamp for when this module is imported
import_time = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", (), None))
with open(LOG_FILE, "a") as f:
    f.write(f"\n\nModule imported at {import_time}\n\n") 