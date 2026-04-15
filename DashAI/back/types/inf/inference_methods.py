import re

import numpy as np
import pandas as pd

import DashAI.back.types.inf.ptype.Machine as Machine
from DashAI.back.types.inf.Inference import InferenceMethod
from DashAI.back.types.inf.ptype.Machines import MACHINES, Machines
from DashAI.back.types.inf.ptype.PtypeCat import PtypeCat
from DashAI.back.types.utils import PTYPE_TO_DASHAI

_REASON_DATE_TYPES = {
    "date-iso-8601",
    "date-eu",
    "date-non-std-subtype",
    "date-non-std",
    "time",
}

_REASON_DATE_PATTERNS = [
    re.compile(r"^\d{1,2}\.\d{1,2}\.\d{2,4}$"),
    re.compile(r"^\d{4}\.\d{1,2}\.\d{1,2}$"),
    re.compile(r"^\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{1,4}$"),
    re.compile(r"^\d{1,2}-\d{1,2}-\d{2,4}$"),
    re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$"),
    re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?$"),
]


def _series_looks_like_date(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(100)
    if len(sample) == 0:
        return False
    matches = sum(
        1 for v in sample if any(p.match(v.strip()) for p in _REASON_DATE_PATTERNS)
    )
    return (matches / len(sample)) > 0.8


class DashAIPtype(PtypeCat, InferenceMethod):
    """
    A class to represent a DashAI Ptype inference method.

    This class extends the InferenceMethod and PtypeCat classes to provide
    functionality for inferring types in DashAI applications.

    Parameters
    ----------
    cat_threshold : float
        Probability threshold for categorical classification.
        Default is 0.7 (stricter than before).
    max_unique_ratio : float
        Maximum ratio of unique values for categorical detection.
    max_unique_count : int
        Maximum number of unique categories allowed.
    """

    def __init__(
        self,
        cat_threshold: float = 0.7,
        max_unique_ratio: float = 0.05,
        max_unique_count: int = 50,
    ):
        super().__init__(
            cat_threshold=cat_threshold,
            max_unique_ratio=max_unique_ratio,
            max_unique_count=max_unique_count,
        )
        self.types.extend(["time", "float_comma"])

        current_machines = {
            **MACHINES,
            "time": Machine.Time(),
            "float_comma": Machine.FloatComma(),
        }

        self.machines = Machines(self.types, current_machines)

    def _build_inference_reason(
        self,
        series: pd.Series,
        ptype_type: str,
        final_type: str,
        dashai_type: str = None,
    ) -> dict:
        """Build a human-auditable explanation for the inferred type.

        Re-derives the same checks used in PtypeCat._is_categorical_candidate
        and returns the rule that drove the decision plus the supporting stats.
        """
        is_categorical = final_type == "categorical"
        total = int(len(series))
        non_null = series.dropna()
        unique_count = int(non_null.nunique()) if total else 0
        unique_ratio = (unique_count / total) if total else 0.0

        sample_values = (
            non_null.drop_duplicates().head(5).astype(str).tolist() if total else []
        )

        reason = {
            "final_type": dashai_type or final_type,
            "ptype_final": final_type,
            "inferred_base_type": ptype_type,
            "is_categorical": is_categorical,
            "unique_count": unique_count,
            "unique_ratio": round(unique_ratio, 4),
            "total_count": total,
            "sample_values": sample_values,
            "thresholds": {
                "max_unique_count": self.max_unique_count,
                "max_unique_ratio": self.max_unique_ratio,
                "cat_threshold": self.cat_threshold,
            },
            "rule": "unknown",
        }

        if total == 0:
            reason["rule"] = "empty_column"
            return reason

        if ptype_type in _REASON_DATE_TYPES:
            if dashai_type == "Text":
                reason["rule"] = "date_detected_mapped_to_text"
            else:
                reason["rule"] = "date_type_excluded"
            return reason

        if ptype_type == "boolean":
            reason["rule"] = "boolean_always_categorical"
            return reason

        if ptype_type not in ("string", "integer", "float"):
            reason["rule"] = "unsupported_base_type"
            return reason

        if ptype_type == "string" and _series_looks_like_date(series):
            reason["rule"] = "string_looks_like_date"
            return reason

        if unique_count > self.max_unique_count:
            reason["rule"] = "too_many_unique_values"
            return reason

        if total >= 20 and unique_ratio > self.max_unique_ratio:
            reason["rule"] = "unique_ratio_above_threshold"
            return reason

        if ptype_type == "string":
            lengths = series.astype(str).str.len()
            mean_len = float(lengths.mean()) if len(lengths) else 0.0
            std_len = float(lengths.std()) if len(lengths) else 0.0
            reason["string_length"] = {
                "mean": round(mean_len, 2),
                "std": round(std_len, 2),
            }
            if mean_len > 50:
                reason["rule"] = "string_too_long"
                return reason
            if std_len > 20 and unique_ratio > 0.3:
                reason["rule"] = "string_high_length_variance"
                return reason

        if ptype_type == "integer":
            if unique_count == total:
                reason["rule"] = "integer_all_unique"
                return reason
            try:
                vals = series.dropna().astype(float).to_numpy()
                if len(vals) > 1:
                    sorted_vals = np.sort(vals)
                    diffs = np.diff(sorted_vals)
                    if np.all(diffs == 1):
                        reason["rule"] = "integer_sequential_range"
                        return reason
                    if np.median(diffs) <= 2 and np.max(diffs) < 5:
                        reason["rule"] = "integer_dense_small_range"
                        return reason
            except (ValueError, TypeError):
                pass

        if ptype_type == "float":
            try:
                vals = series.dropna().astype(float)
                is_whole = np.allclose(vals, vals.astype(int))
                if not is_whole:
                    reason["rule"] = "float_has_decimals"
                    return reason
                reason["float_is_whole"] = True
            except (ValueError, TypeError):
                pass

        if is_categorical:
            if unique_count <= self.max_unique_count and (
                total < 20 or unique_ratio <= self.max_unique_ratio
            ):
                reason["rule"] = "low_cardinality"
            else:
                reason["rule"] = "ml_classifier_categorical"
        else:
            reason["rule"] = "ml_classifier_not_categorical"

        return reason

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

        inferred_types = {}
        for col_name, col_object in schema.cols.items():
            ptype_type = col_object.inferred_type()

            # Map ptype type to DashAI type
            if ptype_type in PTYPE_TO_DASHAI:
                dashai_info = PTYPE_TO_DASHAI[ptype_type].copy()
            else:
                # Fallback to text for unknown types
                dashai_info = {"type": "Text", "dtype": "string"}

            # Handle categorical specially
            # include categories and preserve original dtype
            if ptype_type == "categorical":
                unique_vals = col_object.get_normal_values()
                dashai_info["categories"] = unique_vals

                # Preserve original dtype from pandas DataFrame
                original_dtype = data[col_name].dtype
                if pd.api.types.is_integer_dtype(original_dtype):
                    dashai_info["dtype"] = "int64"
                elif pd.api.types.is_float_dtype(original_dtype):
                    dashai_info["dtype"] = "float64"
                elif pd.api.types.is_bool_dtype(original_dtype):
                    dashai_info["dtype"] = "bool"
                else:
                    dashai_info["dtype"] = "string"

            try:
                if ptype_type == "categorical":
                    pandas_dtype = data[col_name].dtype
                    if pd.api.types.is_bool_dtype(pandas_dtype):
                        base_ptype = "boolean"
                    elif pd.api.types.is_integer_dtype(pandas_dtype):
                        base_ptype = "integer"
                    elif pd.api.types.is_float_dtype(pandas_dtype):
                        base_ptype = "float"
                    else:
                        base_ptype = "string"
                else:
                    base_ptype = ptype_type
                dashai_info["inference_reason"] = self._build_inference_reason(
                    data[col_name],
                    base_ptype,
                    ptype_type,
                    dashai_type=dashai_info.get("type"),
                )
            except Exception:
                dashai_info["inference_reason"] = None

            inferred_types[col_name] = dashai_info

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
                    result = PTYPE_TO_DASHAI["categorical"].copy()
                    result["dtype"] = "string"
                    inferred_types[col] = result
                else:
                    inferred_types[col] = PTYPE_TO_DASHAI["string"]

            elif pd.api.types.is_integer_dtype(dtype):
                n_unique = series.nunique(dropna=True)
                if n_unique < 10:
                    result = PTYPE_TO_DASHAI["categorical"].copy()
                    result["dtype"] = "int64"
                    inferred_types[col] = result
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
