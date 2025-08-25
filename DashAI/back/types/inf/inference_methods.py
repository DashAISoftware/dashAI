from pathlib import Path

import joblib
import pandas as pd

import DashAI.back.types.inf.ptype.Machine as Machine
from DashAI.back.types.dashai_image import DashAIImage
from DashAI.back.types.inf.Inference import InferenceMethod
from DashAI.back.types.inf.ptype.Machines import MACHINES, Machines
from DashAI.back.types.inf.ptype.PtypeCat import PtypeCat
from DashAI.back.types.utils import PTYPE_TO_DASHAI, is_image_path


# DashAI Ptype inference method for type inference in DashAI applications.
class DashAIPtype(PtypeCat, InferenceMethod):
    """

    A class to represent a DashAI Ptype inference method.
    This class extends the InferenceMethod and PtypeCat classes to provide
    functionality for inferring types in DashAI applications.

    """

    def __init__(self):
        self.types = [
            "integer",
            "string",
            "float",
            "boolean",
            "date-iso-8601",
            "date-eu",
            "date-non-std-subtype",
            "date-non-std",
        ]

        # In case of wanting to add a new type:
        # Create the machine in ptype/Machine.py file
        # Add the new machine to the current_machines dictionary.
        # Add the new type to this list.
        self.types.extend(
            [
                "time",
            ]
        )

        current_machines = {**MACHINES, "time": Machine.Time()}

        self.machines = Machines(self.types, current_machines)
        self.verbose = False
        self.lr_clf = joblib.load(Path(__file__).parent / "ptype" / "LR.sav")
        self.scaler = joblib.load(Path(__file__).parent / "ptype" / "scaler.pkl")
        self.cat_threshold = 0.48

    def infer_types(self, data) -> dict:
        """
        Infers types from the provided data using the PtypeCat model.

        Parameters
        ----------
        data : pd.DataFrame
            The input data for type inference.

        Returns
        -------
        dict
            A dictionary mapping column names to inferred types.
        """

        schema = self.schema_fit(data)
        # Convert the schema to a dashai format
        inferred_types = {}
        for col_name, col_object in schema.cols.items():
            inferred_types[col_name] = PTYPE_TO_DASHAI[
                max(col_object.p_t, key=col_object.p_t.get)
            ]

        return inferred_types


# Dummy inference method to avoid letting DashAIPtype alone :)
class DummyCategoricalInference(InferenceMethod):
    """
    A dummy inference method that does nothing.
    This is used to ensure that DashAIPtype is not the only inference method.
    """

    def infer_types(self, data):
        """
        Dummy Inference method that returns a dummy predicted schema.

        Parameters
        ----------
        data : Any
            The input data for type inference.

        Returns
        -------
        dict
            A dummy predicted types schema.
        """
        inferred_types = {}

        for col in data.columns:
            series = data[col]
            dtype = series.dtype

            if dtype == "object" or isinstance(series.dropna().iloc[0], str):
                n_unique = series.nunique(dropna=True)
                if n_unique < 10:
                    inferred_types[col] = PTYPE_TO_DASHAI["categorical"]
                else:
                    inferred_types[col] = PTYPE_TO_DASHAI["string"]

            elif pd.api.types.is_integer_dtype(dtype):
                n_unique = series.nunique(dropna=True)
                if n_unique < 10:
                    inferred_types[col] = PTYPE_TO_DASHAI["categorical"]
                else:
                    inferred_types[col] = PTYPE_TO_DASHAI["integer"]
            elif pd.api.types.is_float_dtype(dtype):
                inferred_types[col] = PTYPE_TO_DASHAI["float"]
            elif pd.api.types.is_bool_dtype(dtype):
                inferred_types[col] = PTYPE_TO_DASHAI["boolean"]
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                inferred_types[col] = PTYPE_TO_DASHAI["date-iso-8601"]
            else:
                inferred_types[col] = PTYPE_TO_DASHAI["string"]
        return inferred_types


class DashAIImageInference:
    """
    Represents a proposed DashAIImage inference method.

    """

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold  # Threshold for image detection confidence

    def infer_types(self, data) -> dict:
        """
        Infer if types in the provided data are images based on a threshold.

        Parameters
        ----------
        data : pd.DataFrame
            The input data for type inference.
        Returns
        -------
        dict
            A dictionary mapping detected image columns to DashAIImage type.
            The other columns are left unchanged.
        """

        inferred_types = {}
        for col in data.columns:
            series = data[col].dropna().astype(str)

            image_like_count = sum(is_image_path(value) for value in series)
            ratio = image_like_count / len(series)

            if ratio >= self.threshold:
                inferred_types[col] = DashAIImage()
            else:
                pass

        return inferred_types
