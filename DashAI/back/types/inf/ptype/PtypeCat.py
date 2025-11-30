# flake8: noqa

from pathlib import Path

import joblib
import numpy as np

from DashAI.back.types.inf.ptype.Machines import Machines
from DashAI.back.types.inf.ptype.Ptype import Ptype

CAT_TRAINED_TYPES = [
    "integer",
    "string",
    "float",
    "boolean",
    "date-iso-8601",
    "date-eu",
    "date-non-std-subtype",
    "date-non-std",
]


class PtypeCat(Ptype):
    """Ptype with categorical detection."""

    def __init__(self, cat_threshold=0.7, max_unique_ratio=0.05, max_unique_count=50):
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
        self.machines = Machines(self.types)
        self.verbose = False
        self.lr_clf = joblib.load(Path(__file__).parent.joinpath("LR.sav"))
        self.scaler = joblib.load(Path(__file__).parent.joinpath("scaler.pkl"))

        # Thresholds
        self.cat_threshold = cat_threshold
        self.max_unique_ratio = max_unique_ratio
        self.max_unique_count = max_unique_count

    def _is_categorical_candidate(self, series, inferred_type):
        """Check if column should be considered for categorical."""
        # Boolean is always categorical
        if inferred_type == "boolean":
            return True

        if inferred_type not in ["string", "integer", "float"]:
            return False

        total = len(series)
        if total == 0:
            return False

        unique_count = series.nunique()
        unique_ratio = unique_count / total

        # Too many unique values
        if unique_count > self.max_unique_count:
            return False

        # High uniqueness ratio (skip for small datasets)
        if total >= 20 and unique_ratio > self.max_unique_ratio:
            return False

        # String-specific: check for free text patterns
        if inferred_type == "string":
            lengths = series.astype(str).str.len()
            if lengths.mean() > 50:  # Long strings = likely free text
                return False
            if lengths.std() > 20 and unique_ratio > 0.3:
                return False

        # Integer-specific: check for IDs
        if inferred_type == "integer":
            # All unique values = likely IDs
            if unique_count == total:
                return False

            try:
                vals = series.dropna().astype(float).values
                if len(vals) > 1:
                    sorted_vals = np.sort(vals)
                    diffs = np.diff(sorted_vals)

                    # Strictly sequential (1,2,3,4...)
                    if np.all(diffs == 1):
                        return False

                    # Nearly sequential (small gaps, like 1,2,4,5,7)
                    # If median diff is 1-2 and max diff < 5, likely IDs
                    if np.median(diffs) <= 2 and np.max(diffs) < 5:
                        return False

                    # Large range with few values = likely codes, not IDs
                    value_range = sorted_vals[-1] - sorted_vals[0]
                    if value_range > 100 and unique_count < 20:
                        return True  # Likely category codes (e.g., country codes)

            except (ValueError, TypeError):
                pass

        # Float-specific: check for discrete codes
        if inferred_type == "float":
            try:
                vals = series.dropna().astype(float)
                is_whole = np.allclose(vals, vals.astype(int))
                if not is_whole and unique_count > 10:
                    return False
            except (ValueError, TypeError):
                pass

        return True

    def _column(self, df, col_name, logP, counts):
        """Returns Column with categorical detection."""
        col = super()._column(df, col_name, logP, counts)
        t_hat = col.inferred_type()

        # Check heuristics first
        if not self._is_categorical_candidate(df[col_name], t_hat):
            col.set_p_t_cat(t_hat, 0.0)
            return col

        # Compute ML probability for eligible types
        if t_hat in ["integer", "string", "float", "boolean"]:
            try:
                feats = col._get_features(counts)
                feats = feats[: len(CAT_TRAINED_TYPES)]
                feats[-2:] = self.scaler.transform(feats[-2:].reshape(1, -1))
                ind = np.where(self.lr_clf.classes_ == "categorical")[0][0]
                p_cat = self.lr_clf.predict_proba(feats.reshape(1, -1))[0][ind]
            except Exception:
                p_cat = 0.0
        else:
            p_cat = 0.0

        # Apply threshold
        if p_cat >= self.cat_threshold:
            col.p_t = {k: 0.0 for k in col.p_t}
            col.p_t["categorical"] = 1.0
            col.type = "categorical"
        else:
            col.set_p_t_cat(t_hat, p_cat)

        return col
