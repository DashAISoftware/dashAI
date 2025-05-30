import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler

from pathlib import Path

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, project_root)

from back.types.inf.ptype import Ptype
from back.types.inf.ptype.Column import Column
from back.types.inf.ptype.Machines import Machines


class PtypeCat(Ptype.Ptype):
    """The PtypeCat cat object. It uses the following data types: categorical, date, integer, float and string."""

    def __init__(self):
        self.types = [
            "integer",
            "string",
            "float",
            "date-iso-8601",
            "date-eu",
            "date-non-std-subtype",
            "date-non-std",
        ]
        self.machines = Machines(self.types)
        self.verbose = False
        self.lr_clf = joblib.load(Path(__file__).parent.joinpath("LR.sav"))
        self.scaler = joblib.load(Path(__file__).parent.joinpath("scaler.pkl"))


    def _column(self, df, col_name, logP, counts):
        """Returns a Column object for a given data column."""
        col = super()._column(df, col_name, logP, counts)

        # ptype-cat
        t_hat = col.inferred_type()
        if t_hat in ["integer", "string"]:
            feats = col._get_features(counts)
            # magic numbers
            feats[-2:] = self.scaler.transform(feats[-2:].reshape(1, -1))
            ind = np.where(self.lr_clf.classes_ == "categorical")[0][0]
            p_cat = self.lr_clf.predict_proba(feats.reshape(1, -1))[0][ind]
        else:
            p_cat = 0.0
        col.set_p_t_cat(t_hat, p_cat)

        return col

