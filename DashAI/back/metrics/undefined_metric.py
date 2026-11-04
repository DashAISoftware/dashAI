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
from typing import Optional


class UndefinedMetricError(Exception):
    """A metric has no value on the data it was asked to score.

    Not a ``ValueError`` nor an ``ArithmeticError`` on purpose: the Optuna
    optimizer catches both as "this trial could not be fitted", and would
    swallow an undefined goal metric into "every trial failed, narrow the
    search", the wrong advice.

    Attributes
    ----------
    reason : str
        Why the metric is undefined, in a sentence a user can act on. With
        ``positions``, the sentence ends where they are named: "and the
        actual value is zero" reads on into "on 2023-05-01.".
    positions : tuple of int, optional
        Where, among the values scored, the ones that leave the metric
        undefined are. The metric knows positions and not what they are
        called; ``describe_undefined`` names them as dates or as rows.
    hint : str, optional
        What to do about it, said after the positions are named.
    """

    def __init__(self, reason: str, positions=None, hint: Optional[str] = None):
        self.reason = reason
        self.positions = (
            tuple(int(p) for p in positions) if positions is not None else None
        )
        self.hint = hint
        super().__init__(describe_undefined(self))


def describe_undefined(undefined: UndefinedMetricError, dates=None) -> str:
    """The reason a metric is undefined, with the values that make it so.

    The same text goes in a metric row's ``unavailable_reason`` and in the
    error of a run that tried to optimize for it. Without positions, the
    reason as the metric gave it.

    Parameters
    ----------
    undefined : UndefinedMetricError
        What the metric raised.
    dates : sequence of datetime-like, optional
        The date of each value scored, in the order the positions count. A
        forecast has them, and the values are named by date, up to five;
        rows scored without dates are counted.

    Returns
    -------
    str
        A sentence, or two with the hint.
    """
    text = undefined.reason
    if undefined.positions:
        if dates is not None:
            import pandas as pd

            from DashAI.back.tasks.time_grid import sample_dates

            at = pd.to_datetime([dates[p] for p in undefined.positions])
            text += f" on {sample_dates(at, more='more dates')}."
        else:
            count = len(undefined.positions)
            text += f" on {count} row{'s' if count != 1 else ''}."
    if undefined.hint:
        text += f" {undefined.hint}"
    return text


@dataclass(frozen=True)
class Unavailable:
    """The result of a metric that had no value, standing where a score would.

    Attributes
    ----------
    reason : str
        Why, as the metric explained it.
    """

    reason: str
