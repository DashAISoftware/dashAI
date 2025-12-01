# flake8: noqa

import numpy as np

from DashAI.back.types.inf.ptype.Column import (
    ANOMALIES_INDEX,
    MISSING_INDEX,
    TYPE_INDEX,
    Column,
    _get_unique_vals,
)
from DashAI.back.types.inf.ptype.Machine import PI
from DashAI.back.types.inf.ptype.Machines import Machines
from DashAI.back.types.inf.ptype.Schema import Schema
from DashAI.back.types.inf.ptype.Trainer import (
    likelihoods_normalize,
    sum_weighted_likelihoods,
)
from DashAI.back.types.inf.ptype.utils import normalize_log_probs


class Ptype:
    """The Ptype object. It uses the following data types: date, integer, float and string."""

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

    def schema_fit(self, df):
        """Run inference for each column in a dataframe.

        :param df: dataframe loaded by reading values as strings.
        :return: Schema object with information about each column.
        """
        df = df.map(str)
        self.machines.normalize_params()
        self.machines.update_values(np.unique(df.values))

        cols = {}
        for _, col_name in enumerate(list(df.columns)):
            unique_vs, counts = _get_unique_vals(df[col_name], return_counts=True)
            probabilities_dict = self.machines.machine_probabilities(unique_vs)
            probabilities = np.array(
                [probabilities_dict[str(x_i)] for x_i in unique_vs]
            )
            cols[col_name] = self._column(df, col_name, probabilities, counts)

        return Schema(df, cols)

    def _column(self, df, col_name, logP, counts):
        """Returns a Column object for a given data column."""
        I, J = logP.shape
        K = J - 2

        p_t = []
        p_z = {}
        counts_array = np.array(counts)

        for k in range(K):
            p_t.append(sum_weighted_likelihoods(counts_array, logP, k))
            x1, x2, x3, log_mx, sm = likelihoods_normalize(PI, logP, k)

            p_z_k = np.zeros((I, 3))
            p_z_k[:, TYPE_INDEX] = np.exp(x1 - log_mx - np.log(sm))
            p_z_k[:, MISSING_INDEX] = np.exp(x2 - log_mx - np.log(sm))
            p_z_k[:, ANOMALIES_INDEX] = np.exp(x3 - log_mx - np.log(sm))
            p_z[self.types[k]] = p_z_k / p_z_k.sum(axis=1)[:, np.newaxis]

        p_t = normalize_log_probs(p_t)
        p_t = {t: p for t, p in zip(self.types, p_t)}

        uniform = np.ones(len(p_t)) / len(p_t)
        if np.allclose(list(p_t.values()), uniform, rtol=1e-2):
            p_t = {t: 1.0 if t == "string" else 0.0 for t in self.types}
            I = logP.shape[0]
            p_z = {"string": np.tile([1.0, 0.0, 0.0], (I, 1))}

        return Column(series=df[col_name], p_t=p_t, p_z=p_z)

    def get_na_values(self):
        return self.machines.missing.alphabet.copy()

    def set_na_values(self, na_values):
        self.machines.missing.alphabet = na_values

    def get_additional_an_values(self):
        return self.machines.anomalous.an_values.copy()

    def set_additional_an_values(self, an_values):
        probs = self.machines.machine_probabilities(an_values)
        ratio = PI[0] / PI[2] + 0.1
        new_probs = {v: np.log(ratio * np.max(np.exp(probs[v]))) for v in an_values}
        self.machines.anomalous.set_an(an_values, new_probs)

    def get_string_alphabet(self):
        string_index = 2 + self.types.index("string")
        return self.machines.machines[string_index].alphabet

    def set_string_alphabet(self, alphabet):
        string_index = 2 + self.types.index("string")
        self.machines.machines[string_index].set_alphabet(alphabet)
