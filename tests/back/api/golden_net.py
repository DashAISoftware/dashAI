"""Record-then-compare plumbing shared by the nets of the exogenous PR.

A net is recorded once on the base, with its environment variable set to
``1``, and compared against that file on every slice after: a diff on the
golden is a behaviour change. Floats are compared to a relative 1e-9, because
the last digits of a BLAS result differ between platforms; everything else
exactly. The same rules as ``test_column_roles_net.py``, kept in one place so
the three nets of RECONCILING_FORECASTING §7.4 cannot drift apart.
"""

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd


class Golden:
    """The recorded values of one net, or the recorder that writes them."""

    def __init__(self, path: Path, env_var: str) -> None:
        self.path = path
        self.recording = os.environ.get(env_var) == "1"
        self._recorded: dict = {}
        self._values = (
            None if self.recording else json.loads(path.read_text(encoding="utf-8"))
        )

    def pin(
        self, key: str, value, rel_tol: float = 1e-9, abs_tol: float = 1e-12
    ) -> None:
        value = json.loads(json.dumps(plain(value)))
        if self.recording:
            self._recorded[key] = value
            return
        assert key in self._values, f"{key} was never recorded"
        if not same(value, self._values[key], rel_tol, abs_tol):
            assert value == self._values[key], key

    def save(self) -> None:
        """Merge what this run recorded into the file. A no-op when comparing."""
        if not self.recording:
            return
        existing = (
            json.loads(self.path.read_text(encoding="utf-8"))
            if self.path.exists()
            else {}
        )
        existing.update(self._recorded)
        self.path.write_text(
            json.dumps(existing, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )


def plain(value):
    """A JSON-comparable copy: numpy scalars and arrays, tuples and frames."""
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, pd.DataFrame):
        return plain(value.to_dict(orient="list"))
    if isinstance(value, pd.Series):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def same(value, expected, rel_tol: float = 1e-9, abs_tol: float = 1e-12) -> bool:
    """Equal, floats to ``rel_tol`` or ``abs_tol``, everything else exactly."""
    if isinstance(value, float) or isinstance(expected, float):
        numbers = (int, float)
        return (
            isinstance(value, numbers)
            and isinstance(expected, numbers)
            and not isinstance(value, bool)
            and not isinstance(expected, bool)
            and math.isclose(value, expected, rel_tol=rel_tol, abs_tol=abs_tol)
        )
    if isinstance(value, dict) and isinstance(expected, dict):
        return value.keys() == expected.keys() and all(
            same(value[k], expected[k], rel_tol, abs_tol) for k in value
        )
    if isinstance(value, list) and isinstance(expected, list):
        return len(value) == len(expected) and all(
            same(v, e, rel_tol, abs_tol) for v, e in zip(value, expected, strict=True)
        )
    return value == expected
