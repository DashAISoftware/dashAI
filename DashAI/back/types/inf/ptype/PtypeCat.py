# flake8: noqa

import re
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

DATE_TYPES = [
    "date-iso-8601",
    "date-eu",
    "date-non-std-subtype",
    "date-non-std",
    "time",
]

DATE_PATTERNS = [
    # DD.MM.YYYY or DD.MM.YY
    r"^\d{1,2}\.\d{1,2}\.\d{2,4}$",
    # YYYY.MM.DD
    r"^\d{4}\.\d{1,2}\.\d{1,2}$",
    # DD/MM/YYYY, MM/DD/YYYY, YYYY/MM/DD
    r"^\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{1,4}$",
    # DD-MM-YYYY or similar
    r"^\d{1,2}-\d{1,2}-\d{2,4}$",
    # Time patterns HH:MM:SS or HH:MM
    r"^\d{1,2}:\d{2}(:\d{2})?$",
    # Datetime: YYYY-MM-DD HH:MM:SS
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?$",
]


def _looks_like_date(series) -> bool:
    """Check if most values in series look like dates/times."""
    sample = series.dropna().astype(str).head(100)
    if len(sample) == 0:
        return False

    match_count = 0
    for val in sample:
        val = val.strip()
        for pattern in DATE_PATTERNS:
            if re.match(pattern, val):
                match_count += 1
                break
    return (match_count / len(sample)) > 0.8


class PtypeCat(Ptype):
    """Ptype with categorical detection."""

    def __init__(self, cat_threshold=0.7, max_unique_ratio=0.05, max_unique_count=50):
        super().__init__()
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

        if inferred_type in DATE_TYPES:
            return False

        # Boolean is always categorical
        if inferred_type == "boolean":
            return True

        if inferred_type not in ["string", "integer", "float"]:
            return False

        total = len(series)
        if total == 0:
            return False

        if inferred_type == "string":
            if _looks_like_date(series):
                return False

        unique_count = series.nunique()
        unique_ratio = unique_count / total

        if unique_count > self.max_unique_count:
            return False

        if total >= 20 and unique_ratio > self.max_unique_ratio:
            return False

        if inferred_type == "string":
            lengths = series.astype(str).str.len()
            if lengths.mean() > 50:
                return False
            if lengths.std() > 20 and unique_ratio > 0.3:
                return False

        if inferred_type == "integer":
            if unique_count == total:
                return False

            try:
                vals = series.dropna().astype(float).values
                if len(vals) > 1:
                    sorted_vals = np.sort(vals)
                    diffs = np.diff(sorted_vals)

                    if np.all(diffs == 1):
                        return False

                    if np.median(diffs) <= 2 and np.max(diffs) < 5:
                        return False

                    value_range = sorted_vals[-1] - sorted_vals[0]
                    if value_range > 100 and unique_count < 20:
                        return True

            except (ValueError, TypeError):
                pass

        if inferred_type == "float":
            try:
                vals = series.dropna().astype(float)
                is_whole = np.allclose(vals, vals.astype(int))
                # Real floats (with decimals) should never be categorical
                if not is_whole:
                    return False
            except (ValueError, TypeError):
                pass

        return True

    def _column(self, df, col_name, logP, counts):
        """Returns Column with categorical detection."""
        col = super()._column(df, col_name, logP, counts)
        t_hat = col.inferred_type()

        if not self._is_categorical_candidate(df[col_name], t_hat):
            col.set_p_t_cat(t_hat, 0.0)
            return col

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

        if p_cat >= self.cat_threshold:
            col.p_t = {k: 0.0 for k in col.p_t}
            col.p_t["categorical"] = 1.0
            col.type = "categorical"
        else:
            col.set_p_t_cat(t_hat, p_cat)

        return col
