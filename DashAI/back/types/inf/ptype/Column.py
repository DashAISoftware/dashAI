# flake8: noqa

from collections import OrderedDict
from enum import Enum

import numpy as np

TYPE_INDEX = 0
MISSING_INDEX = 1
ANOMALIES_INDEX = 2


def _get_unique_vals(col, return_counts=False):
    """List of the unique values found in a column."""
    return np.unique([str(x) for x in col.tolist()], return_counts=return_counts)


# Use same names and values as the constants in Model.py. Could consolidate.
class _Status(Enum):
    TYPE = 1
    MISSING = 2
    ANOMALOUS = 3


class _Feature(Enum):
    U_RATIO = 5
    U_RATIO_CLEAN = 6
    U = 7
    U_CLEAN = 8


class Column:
    def __init__(self, series, p_t, p_z):
        self.series = series
        self.p_t = p_t
        self.p_z = p_z
        self.type = self.inferred_type()
        self.unique_vals, self.unique_vals_counts = _get_unique_vals(
            self.series, return_counts=True
        )
        self._initialise_missing_anomalies()

    def __repr__(self):
        return repr(self.__dict__)

    def _initialise_missing_anomalies(self):
        row_posteriors = self.p_z[self.type]
        max_row_posterior_indices = np.argmax(row_posteriors, axis=1)

        self.normal_indices = list(np.where(max_row_posterior_indices == TYPE_INDEX)[0])
        self.missing_indices = list(
            np.where(max_row_posterior_indices == MISSING_INDEX)[0]
        )
        self.anomalous_indices = list(
            np.where(max_row_posterior_indices == ANOMALIES_INDEX)[0]
        )

    def inferred_type(self):
        """Get most likely inferred type for the column."""
        return max(self.p_t, key=self.p_t.get)

    def get_normal_ratio(self):
        """Get proportion of unique values in the column which are considered neither anomalous nor missing."""
        return round(
            sum(self.unique_vals_counts[self.normal_indices])
            / sum(self.unique_vals_counts),
            2,
        )

    def get_na_ratio(self):
        """Get proportion of unique values in the column which are considered 'missing'."""
        return round(
            sum(self.unique_vals_counts[self.missing_indices])
            / sum(self.unique_vals_counts),
            2,
        )

    def get_an_ratio(self):
        """Get proportion of unique values in the column which are considered 'anomalous'."""
        return round(
            sum(self.unique_vals_counts[self.anomalous_indices])
            / sum(self.unique_vals_counts),
            2,
        )

    def get_normal_values(self):
        """Get list of all values in the column which are considered neither anomalous nor missing."""
        return list(self.unique_vals[self.normal_indices])

    def get_na_values(self):
        """Get a list of the values in the column which are considered 'missing'."""
        return list(self.unique_vals[self.missing_indices])

    def get_an_values(self):
        """Get a list of the values in the column which are considered 'anomalous'."""
        return list(self.unique_vals[self.anomalous_indices])

    def reclassify(self, new_t):
        """Assign a different type to the column, and adjust the interpretation of missing/anomalous values
        accordingly.

        :param new_t: the new type, which must be one of the types known to ptype.
        """
        if new_t not in self.p_z:
            raise Exception(f"Type {new_t} is unknown.")
        self.type = new_t
        self._initialise_missing_anomalies()

    def _get_features(self, counts):
        posterior = OrderedDict()
        # handle equal probs
        for t, p in sorted(self.p_t.items()):
            # aggregate date subtypes
            t_0 = t.split("-")[0]
            if t_0 in posterior.keys():
                posterior[t_0] += p
            else:
                posterior[t_0] = p
        posterior = posterior.values()

        entries = [str(int_element) for int_element in self.series.tolist()]
        U = len(np.unique(entries))
        U_clean = len(self.normal_indices)

        N = len(entries)
        N_clean = sum([counts[index] for index in self.normal_indices])

        u_ratio = U / N
        if U_clean == 0 and N_clean == 0:
            u_ratio_clean = 0.0
        else:
            u_ratio_clean = U_clean / N_clean

        return np.array(list(posterior) + [u_ratio, u_ratio_clean, U, U_clean])

    def set_p_t_cat(self, t_hat, p_cat):
        self.p_t["categorical"] = self.p_t[t_hat] * p_cat
        self.p_t[t_hat] = 1 - self.p_t["categorical"]
        self.type = self.inferred_type()
