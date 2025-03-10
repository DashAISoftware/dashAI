"""DashAI CSV Type Inference Dataloader."""

import os
import shutil
import re
import logging
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
        """Analyze a column of string values to determine if it contains image paths.
        
        Parameters
        ----------
        column_values : List[str]
            List of string values from a column
            
        Returns
        -------
        Tuple[bool, float, Dict[str, Any]]
            A tuple containing (is_image_column, confidence_score, image_stats)
        """
        # Direct print for visibility
        print(f"Analyzing column with {len(column_values)} values")
        
        # Filter out None values
        valid_values = [v for v in column_values if v is not None]
        
        if not valid_values:
            print("No valid values found in column")
            return False, 0.0, {}
            
        # Count how many values look like image paths
        image_path_count = sum(1 for v in valid_values if self._is_image_path(v))
        
        # Calculate the percentage of values that look like image paths
        image_path_percentage = image_path_count / len(valid_values)
        
        # Determine if this is an image column based on the threshold
        is_image_column = image_path_percentage >= self.IMAGE_THRESHOLD
        
        # Print detailed analysis information
        analysis_msg = f"Column analysis: {image_path_count}/{len(valid_values)} values look like image paths ({image_path_percentage:.2%})"
        print(analysis_msg)
        logger.info(analysis_msg)
        
        result_msg = f"Is image column: {is_image_column} (threshold: {self.IMAGE_THRESHOLD:.2%})"
        print(result_msg)
        logger.info(result_msg)
        
        # If we have some image paths but not enough to meet the threshold, show a sample
        if 0 < image_path_percentage < self.IMAGE_THRESHOLD:
            sample_values = [v for v in valid_values[:10] if self._is_image_path(v)]
            if sample_values:
                sample_msg = f"Sample image paths detected but below threshold: {sample_values[:3]}"
                print(sample_msg)
                logger.info(sample_msg)
        
        # Direct write to log file
        with open(LOG_FILE, "a") as f:
            f.write(f"Column analysis: {image_path_count}/{len(valid_values)} values look like image paths ({image_path_percentage:.2%})\n")
            f.write(f"Is image column: {is_image_column} (threshold: {self.IMAGE_THRESHOLD:.2%})\n")
        
        # If this is an image column, verify which paths exist and can be loaded
        image_stats = {}
        if is_image_column:
            print("Verifying image paths...")
            # Get all values that look like image paths
            potential_image_paths = [v for v in valid_values if self._is_image_path(v)]
            
            # Verify which paths exist and can be loaded
            valid_paths, invalid_paths, _ = self._verify_image_paths(potential_image_paths)
            
            # Calculate statistics
            total_images = len(potential_image_paths)
            valid_count = len(valid_paths)
            invalid_count = len(invalid_paths)
            valid_percentage = valid_count / total_images if total_images > 0 else 0
            
            # Store statistics
            image_stats = {
                "total_images": total_images,
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "valid_percentage": valid_percentage,
                "valid_paths": valid_paths[:10],  # Store first 10 valid paths as examples
                "invalid_paths": invalid_paths[:10],  # Store first 10 invalid paths as examples
            }
            
            # Log statistics
            stats_msg = (
                f"Image path verification: {valid_count}/{total_images} paths are valid ({valid_percentage:.2%})\n"
                f"  - Valid paths (first 5): {valid_paths[:5]}\n"
                f"  - Invalid paths (first 5): {invalid_paths[:5]}"
            )
            print(stats_msg)
            logger.info(stats_msg)
            
            # Direct write to log file
            with open(LOG_FILE, "a") as f:
                f.write(f"Image path verification: {valid_count}/{total_images} paths are valid ({valid_percentage:.2%})\n")
                if valid_paths:
                    f.write(f"Sample valid paths: {valid_paths[:5]}\n")
                if invalid_paths:
                    f.write(f"Sample invalid paths: {invalid_paths[:5]}\n")
        
        return is_image_column, image_path_percentage, image_stats
    
    def _detect_image_columns(self, dataset: DatasetDict) -> DatasetDict:
        """Process the dataset to detect and mark image columns.
        
        Parameters
        ----------
        dataset : DatasetDict
            The original dataset
            
        Returns
        -------
        DatasetDict
            The processed dataset with image columns marked
        """
        processed_dataset = DatasetDict()
        
        start_msg = "=== Starting Image Column Detection ==="
        print(f"\n{start_msg}")
        logger.info(start_msg)
        
        # Dictionary to store image column statistics for all splits
        all_image_stats = {}
        
        for split_name, split_dataset in dataset.items():
            split_msg = f"Analyzing split: '{split_name}'"
            print(f"\n{split_msg}")
            logger.info(split_msg)
            
            # Get the current features
            features = split_dataset.features
            new_features = {}
            
            # Track which columns should be converted to Image type
            image_columns = []
            
            # Store image statistics for this split
            split_image_stats = {}
            
            # Analyze each string column
            for column_name, feature_type in features.items():
                if isinstance(feature_type, Value) and feature_type.dtype == 'string':
                    col_msg = f"Analyzing column: '{column_name}' (type: string)"
                    print(f"\n{col_msg}")
                    logger.info(col_msg)
                    
                    # Get all values for this column
                    column_values = split_dataset[column_name]
                    
                    # Analyze if this column contains image paths
                    analyze_msg = f"Analyzing {len(column_values)} values in column '{column_name}'..."
                    print(analyze_msg)
                    logger.info(analyze_msg)
                    
                    is_image_column, confidence, image_stats = self._analyze_string_column(column_values)
                    
                    if is_image_column:
                        # Mark this column as an image column, but keep it as string to avoid loading issues
                        # new_features[column_name] = Image()  # This would try to load the images
                        new_features[column_name] = feature_type  # Keep as string but mark for future reference
                        image_columns.append(column_name)
                        
                        # Store image statistics for this column
                        split_image_stats[column_name] = image_stats
                        
                        success_msg = f"✅ Column '{column_name}' identified as image column with {confidence:.2%} confidence"
                        print(success_msg)
                        logger.info(success_msg)
                        
                        # Show some sample values that were identified as images
                        sample_values = [v for v in column_values[:5] if v is not None and self._is_image_path(v)]
                        if sample_values:
                            sample_msg = f"Sample image paths: {sample_values}"
                            print(sample_msg)
                            logger.info(sample_msg)
                            
                        # Add a warning about not converting to Image type to avoid errors
                        warning_msg = f"⚠️ Column '{column_name}' contains image paths but keeping as string type to avoid loading errors"
                        print(warning_msg)
                        logger.warning(warning_msg)
                        
                        # Report on valid and invalid image paths
                        if image_stats:
                            valid_count = image_stats["valid_count"]
                            total_images = image_stats["total_images"]
                            valid_percentage = image_stats["valid_percentage"]
                            
                            if valid_count == total_images:
                                path_msg = f"✅ All {valid_count} image paths in column '{column_name}' are valid and can be loaded"
                            elif valid_count == 0:
                                path_msg = f"❌ None of the {total_images} image paths in column '{column_name}' could be loaded"
                            else:
                                path_msg = f"⚠️ {valid_count}/{total_images} image paths in column '{column_name}' are valid ({valid_percentage:.2%})"
                            
                            print(path_msg)
                            logger.info(path_msg)
                    else:
                        # Keep the original feature type
                        new_features[column_name] = feature_type
                        
                        fail_msg = f"❌ Column '{column_name}' is not an image column (confidence: {confidence:.2%})"
                        print(fail_msg)
                        logger.info(fail_msg)
                else:
                    # Keep non-string columns as they are
                    new_features[column_name] = feature_type
                    
                    skip_msg = f"Skipping column '{column_name}' (type: {feature_type.dtype})"
                    print(skip_msg)
                    logger.info(skip_msg)
            
            # Create a new dataset with the updated features
            processed_split = split_dataset
            
            # Instead of converting to Image type, we'll add metadata to mark image columns
            if image_columns:
                convert_msg = f"\n✅ Identified {len(image_columns)} image columns in split '{split_name}':"
                print(convert_msg)
                logger.info(convert_msg)
                
                for col in image_columns:
                    col_msg = f"  - {col}"
                    print(col_msg)
                    logger.info(col_msg)
                
                # Add metadata to the dataset to mark image columns
                info = processed_split.info
                if not hasattr(info, 'image_columns'):
                    info.image_columns = image_columns
                
                # Add image statistics to metadata
                if not hasattr(info, 'image_stats'):
                    info.image_stats = split_image_stats
                
                # Store image statistics for this split
                all_image_stats[split_name] = split_image_stats
                
                # Log that we're not converting to Image type to avoid errors
                info_msg = f"⚠️ Image columns are marked in dataset metadata but kept as string type to avoid loading errors"
                print(info_msg)
                logger.info(info_msg)
            else:
                no_cols_msg = f"\n❌ No image columns detected in split '{split_name}'"
                print(no_cols_msg)
                logger.info(no_cols_msg)
            
            processed_dataset[split_name] = processed_split
        
        # Generate a summary report of all image columns and their statistics
        if all_image_stats:
            summary_msg = "\n=== Image Column Summary Report ===\n"
            
            for split_name, split_stats in all_image_stats.items():
                summary_msg += f"\nSplit: '{split_name}'\n"
                
                for column_name, stats in split_stats.items():
                    valid_count = stats["valid_count"]
                    total_images = stats["total_images"]
                    valid_percentage = stats["valid_percentage"]
                    
                    summary_msg += f"  Column: '{column_name}'\n"
                    summary_msg += f"    - Total image paths: {total_images}\n"
                    summary_msg += f"    - Valid image paths: {valid_count} ({valid_percentage:.2%})\n"
                    summary_msg += f"    - Invalid image paths: {stats['invalid_count']}\n"
                    
                    if stats["valid_paths"]:
                        summary_msg += f"    - Sample valid paths: {stats['valid_paths'][:3]}\n"
                    if stats["invalid_paths"]:
                        summary_msg += f"    - Sample invalid paths: {stats['invalid_paths'][:3]}\n"
            
            print(summary_msg)
            logger.info(summary_msg)
            
            # Write summary to log file
            with open(LOG_FILE, "a") as f:
                f.write(summary_msg)
        
        complete_msg = "=== Image Column Detection Complete ==="
        print(f"\n{complete_msg}\n")
        logger.info(complete_msg)
        
        return processed_dataset

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