"""A metric that has no value on some data, and says why.

MAPE divides by each actual value, so a series with a zero in it has no MAPE:
leaving those rows out would report the error of a different series, and
averaging an infinity would report nothing useful. A metric in that position
raises ``UndefinedMetricError`` with the reason, and the caller decides what
it means:

- scoring a run, the metric is recorded as unavailable, with the reason, and
  the run goes on;
- optimizing for it, there is nothing to optimize, and the run stops with an
  error that says so.
"""

from dataclasses import dataclass


class UndefinedMetricError(Exception):
    """A metric has no value on the data it was asked to score.

    Not a ``ValueError`` nor an ``ArithmeticError`` on purpose: the Optuna
    optimizer catches both as "this trial could not be fitted", and would
    swallow an undefined goal metric into "every trial failed, narrow the
    search", the wrong advice.

    Attributes
    ----------
    reason : str
        Why the metric is undefined, in a sentence a user can act on.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Unavailable:
    """The result of a metric that had no value, standing where a score would.

    Attributes
    ----------
    reason : str
        Why, as the metric explained it.
    """

    reason: str
