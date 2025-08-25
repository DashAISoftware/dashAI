# flake8: noqa

from pathlib import Path

import joblib
import numpy as np
from DashAI.back.types.inf.ptype import Ptype
from DashAI.back.types.inf.ptype.Machines import Machines

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


class PtypeCat(Ptype.Ptype):
    """The PtypeCat cat object. It uses the following data types: categorical, date, integer, float and string."""

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
        self.machines = Machines(self.types)
        self.verbose = False
        self.lr_clf = joblib.load(Path(__file__).parent.joinpath("LR.sav"))
        self.scaler = joblib.load(Path(__file__).parent.joinpath("scaler.pkl"))
        self.cat_threshold = 0.5  # Threshold for categorical inference

    def _column(self, df, col_name, logP, counts):
        """Returns a Column object for a given data column."""
        col = super()._column(df, col_name, logP, counts)

        # ptype-cat
        t_hat = col.inferred_type()
        if t_hat in ["integer", "string"]:
            feats = col._get_features(counts)
            feats = feats[: len(CAT_TRAINED_TYPES)]
            # magic numbers
            feats[-2:] = self.scaler.transform(feats[-2:].reshape(1, -1))
            ind = np.where(self.lr_clf.classes_ == "categorical")[0][0]
            p_cat = self.lr_clf.predict_proba(feats.reshape(1, -1))[0][ind]
        else:
            p_cat = 0.0

        if p_cat > self.cat_threshold and t_hat == "string":
            col.p_t = {k: 0.0 for k in col.p_t}
            col.p_t["categorical"] = 1.0
        else:
            col.set_p_t_cat(t_hat, p_cat)

        return col
