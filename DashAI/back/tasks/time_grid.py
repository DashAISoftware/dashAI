"""The regular grid a series has to sit on before a forecaster sees it.

A forecaster reads a series by position and counts its horizon in steps, so
every step has to be one period of a single frequency: no period missing, none
repeated, no date absent. These helpers order a series by time, check it sits
on such a grid and name the frequency. They refuse what does not fit with a
message that says what failed and where, and never correct anything: filling a
gap or dropping a duplicate is a modelling decision, and the notebook is where
the user makes it (``TimeResampler``, an imputer).

They are module helpers, not methods of the forecasting family, because not
every kind of forecasting has a grid: a task over irregular dates would order
its rows and validate nothing. ``SingleSeriesForecastingTask`` calls them; a
panel task would call them once per series.
"""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import pandas as pd

FIX_HINT = (
    "Fix it in the notebook before training: TimeResampler puts a series on a "
    "regular grid and fills the periods it lacks, and an imputer fills empty "
    "values."
)

# How many offending dates a message names before it summarises the rest.
SAMPLE_SIZE = 5


@dataclass(frozen=True)
class TimeGrid:
    """The grid a validated series sits on.

    Attributes
    ----------
    freq : str
        The pandas frequency alias of one step, for instance ``"MS"``.
    first, last : pandas.Timestamp
        The dates of the first and the last step.
    n_steps : int
        How many steps the series has.
    """

    freq: str
    first: "pd.Timestamp"
    last: "pd.Timestamp"
    n_steps: int

    def dates(self, start: int, count: int) -> "pd.DatetimeIndex":
        """The dates of ``count`` steps from step ``start`` (0 is the first).

        A start at or past ``n_steps`` reaches past the end of the series,
        which is how a forecast's dates are named.
        """
        import pandas as pd

        return pd.date_range(self.first, periods=start + count, freq=self.freq)[start:]

    def to_ref(self) -> Dict[str, Any]:
        """The grid as plain JSON, for a context ref or a file."""
        return {
            "freq": self.freq,
            "first": self.first.isoformat(),
            "last": self.last.isoformat(),
            "n_steps": self.n_steps,
        }

    @classmethod
    def from_ref(cls, ref: Dict[str, Any]) -> "TimeGrid":
        """Rebuild a grid from ``to_ref``'s output."""
        import pandas as pd

        return cls(
            freq=ref["freq"],
            first=pd.Timestamp(ref["first"]),
            last=pd.Timestamp(ref["last"]),
            n_steps=int(ref["n_steps"]),
        )


def time_order(dates: "pd.Series") -> List[int]:
    """The positions that put ``dates`` in time order.

    The sort is stable, so rows that share a date keep the order they came in,
    and empty dates go last. Validation refuses both cases afterwards; the
    order only has to be reproducible until then.

    Parameters
    ----------
    dates : pandas.Series
        Parsed datetimes, ``NaT`` where a date is empty.

    Returns
    -------
    list of int
        Positions into ``dates``.
    """
    return list(dates.reset_index(drop=True).sort_values(kind="mergesort").index)


def _sample(dates) -> str:
    """Name up to ``SAMPLE_SIZE`` dates, and how many more there are."""
    named = [
        date.strftime("%Y-%m-%d %H:%M:%S").removesuffix(" 00:00:00") for date in dates
    ]
    shown = ", ".join(named[:SAMPLE_SIZE])
    rest = len(named) - SAMPLE_SIZE
    return f"{shown} and {rest} more" if rest > 0 else shown


def infer_grid_frequency(index: "pd.DatetimeIndex") -> Optional[str]:
    """Name the frequency of sorted, distinct dates, gaps allowed.

    A series with a gap has no frequency as a whole, but its regular
    stretches do: the alias most of them agree on is the candidate. When no
    three consecutive dates are regular, the smallest gap between two dates is
    tried as a fixed step (a day, an hour, a week); a calendar step such as a
    month has no fixed length and needs a regular stretch. A candidate is kept
    only if every date sits on its grid, so a gap reads as missing periods
    while dates that drift off any grid read as no frequency.

    Parameters
    ----------
    index : pandas.DatetimeIndex
        Distinct dates in ascending order.

    Returns
    -------
    str or None
        A pandas frequency alias, or ``None`` when there is none to infer
        (fewer than three dates, or no grid holds them all).
    """
    import pandas as pd

    if len(index) < 3:
        return None
    try:
        alias = pd.infer_freq(index)
    except ValueError:
        alias = None
    if alias is not None:
        return alias

    votes: Counter = Counter()
    for start in range(len(index) - 2):
        try:
            window = pd.infer_freq(index[start : start + 3])
        except ValueError:
            window = None
        if window is not None:
            votes[window] += 1
    if votes:
        alias = votes.most_common(1)[0][0]
    else:
        smallest = index.to_series().diff().dropna().min()
        alias = pd.tseries.frequencies.to_offset(smallest).freqstr

    grid = pd.date_range(index[0], index[-1], freq=alias)
    return alias if index.difference(grid).empty else None


def validate_grid(dates: "pd.Series", values: "pd.Series") -> TimeGrid:
    """Check a series in time order sits on a regular grid.

    The checks run in this order, and the first that fails is the one
    reported: an empty date, a repeated date, no frequency to infer, a missing
    period, an empty value.

    Parameters
    ----------
    dates : pandas.Series
        Parsed datetimes in time order, ``NaT`` where a date is empty.
    values : pandas.Series
        The series' values, aligned with ``dates``.

    Returns
    -------
    TimeGrid
        The grid the series sits on.

    Raises
    ------
    ValueError
        Naming what failed and where, and how to fix it in the notebook.
    """
    import pandas as pd

    dates = pd.Series(pd.to_datetime(dates)).reset_index(drop=True)
    values = pd.Series(values).reset_index(drop=True)

    empty = int(dates.isna().sum())
    if empty:
        raise ValueError(
            f"The time index has {empty} row(s) with no date, and a forecast "
            f"needs every row placed in time. {FIX_HINT}"
        )

    repeated = dates[dates.duplicated(keep=False)]
    if not repeated.empty:
        counts = repeated.value_counts().sort_index()
        named = _sample(counts.index)
        raise ValueError(
            f"The time index repeats {len(counts)} date(s): {named}. A series "
            f"holds one value per period, so each date can appear only once. "
            f"{FIX_HINT}"
        )

    index = pd.DatetimeIndex(dates)
    freq = infer_grid_frequency(index)
    if freq is None:
        raise ValueError(
            f"The dates from {_sample([index[0]])} to {_sample([index[-1]])} do "
            "not follow a regular frequency, so the steps of a forecast cannot "
            f"be counted. {FIX_HINT}"
        )

    missing = pd.date_range(index[0], index[-1], freq=freq).difference(index)
    if not missing.empty:
        raise ValueError(
            f"The series misses {len(missing)} period(s) of its {freq} grid: "
            f"{_sample(missing)}. A forecaster reads the series by position, so "
            f"a missing period would shift every step after it. {FIX_HINT}"
        )

    blank = values.isna()
    if blank.any():
        raise ValueError(
            f"The series has {int(blank.sum())} empty value(s), at "
            f"{_sample(index[blank.to_numpy()])}. {FIX_HINT}"
        )

    return TimeGrid(freq=freq, first=index[0], last=index[-1], n_steps=len(index))
