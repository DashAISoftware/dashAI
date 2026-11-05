"""Helpers for reading DashAI ``Date`` columns.

A ``Date`` column is stored as text plus a strptime format, so anything that
needs real datetimes has to parse first. This module is the only place that
does, because text ordering agrees with chronological ordering for ISO layouts
alone: ``"31-01-2020" < "01-02-2020"`` holds as text and fails as dates.
"""

from typing import TYPE_CHECKING, Any, Final, List, Optional, Union

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

# The strptime format a Date column falls back to when nothing better is known.
DEFAULT_DATE_FORMAT: Final[str] = "%Y-%m-%d"

# Layouts ``pandas.guess_datetime_format`` does not produce. Two digit years
# are the ones that matter: it returns None for "1/31/20". They are grouped by
# component ordering so a day first hint can put the day first candidates ahead
# of the month first ones, which is the only thing separating "01/02/20" from
# itself read the other way round.
_DAY_FIRST_EXTRA: Final[List[str]] = ["%d/%m/%y", "%d-%m-%y", "%d.%m.%y"]
_MONTH_FIRST_EXTRA: Final[List[str]] = ["%m/%d/%y", "%m-%d-%y"]
_YEAR_FIRST_EXTRA: Final[List[str]] = ["%y-%m-%d", "%y/%m/%d"]

EXTRA_DATE_FORMATS: Final[List[str]] = (
    _MONTH_FIRST_EXTRA + _DAY_FIRST_EXTRA + _YEAR_FIRST_EXTRA
)

# How many distinct values are handed to the format guesser. A single value can
# be ambiguous ("01/02/2020"); a handful rarely all are.
_SAMPLE_SIZE: Final[int] = 5


def _as_clean_text(values: Any) -> "pd.Series":
    """Normalise a column to stripped text with blanks treated as missing.

    Parameters
    ----------
    values : Any
        The column values. Anything ``pandas.Series`` accepts.

    Returns
    -------
    pandas.Series
        A string dtype series where empty and whitespace only entries are NA.
    """
    import pandas as pd  # local import

    series = values if isinstance(values, pd.Series) else pd.Series(list(values))
    text = series.reset_index(drop=True).astype("string").str.strip()
    return text.mask(text == "")


def _names_a_full_date(date_format: str) -> bool:
    """Check that a strptime format pins down a specific day.

    A format naming only a year and a month, such as ``"%Y-%m"``, parses
    cleanly but silently invents a day of the month. Treating such a column as
    a Date would hand every consumer a date the data never stated, so those
    columns are better left as text.

    Parameters
    ----------
    date_format : str
        The strptime format to check.

    Returns
    -------
    bool
        ``True`` when the format names a day, a month and a year.
    """
    has_day = "%d" in date_format
    has_month = any(token in date_format for token in ("%m", "%b", "%B"))
    has_year = "%Y" in date_format or "%y" in date_format
    return has_day and has_month and has_year


def _lies_on_a_grid(dates: "pd.Series") -> bool:
    """Check whether parsed dates sit on a regular calendar frequency.

    Parameters
    ----------
    dates : pandas.Series
        Parsed datetimes, possibly unsorted, repeated or missing.

    Returns
    -------
    bool
        ``True`` when the distinct dates, sorted, follow a frequency
        ``pandas.infer_freq`` recognises.
    """
    import pandas as pd  # local import

    index = pd.DatetimeIndex(dates.dropna().drop_duplicates().sort_values())
    if len(index) < 3:
        return False
    try:
        return pd.infer_freq(index) is not None
    except ValueError:
        return False


def parse_date_column(values: Any, format: str = DEFAULT_DATE_FORMAT) -> "pd.Series":
    """Parse a column of date strings into datetimes.

    Parameters
    ----------
    values : Any
        The column values to parse.
    format : str, optional
        A strptime format such as ``"%d/%m/%Y"``. Defaults to
        ``DEFAULT_DATE_FORMAT``.

    Returns
    -------
    pandas.Series
        The parsed datetimes. Missing and blank entries stay ``NaT``.

    Raises
    ------
    ValueError
        If any non-missing value does not match ``format``. The message names
        up to three of the offending values.
    """
    import pandas as pd  # local import

    text = _as_clean_text(values)
    parsed = pd.to_datetime(text, format=format, errors="coerce")

    failed = text.notna() & parsed.isna()
    if failed.any():
        sample = ", ".join(repr(value) for value in text[failed].unique()[:3])
        raise ValueError(
            f"{int(failed.sum())} value(s) do not match the date format "
            f"'{format}': {sample}"
        )

    return parsed


def format_date_column(values: Any, format: str = DEFAULT_DATE_FORMAT) -> "pa.Array":
    """Render a column of real dates, times or timestamps as text.

    Loaders such as the Excel one hand over native temporal columns, while a
    ``Date`` column is stored as text that ``format`` parses back. A plain cast
    to string would write ``"1990-01-01 00:00:00.000000000"`` whatever the
    format says, so the values are rendered through the format instead.

    Parameters
    ----------
    values : pyarrow.Array or pyarrow.ChunkedArray
        A date, time or timestamp column.
    format : str, optional
        The strftime format to render with. Defaults to
        ``DEFAULT_DATE_FORMAT``.

    Returns
    -------
    pyarrow.Array
        A string array. Missing values stay null.
    """
    import pyarrow as pa  # local import

    rendered = [
        None if value is None else value.strftime(format)
        for value in values.to_pylist()
    ]
    return pa.array(rendered, type=pa.string())


def detect_date_format(values: Any, hint: Optional[str] = None) -> Optional[str]:
    """Find a strptime format that reads every value in a column.

    Candidates come from ``pandas.guess_datetime_format`` applied to a sample
    of the values under both day first and month first readings, followed by
    ``EXTRA_DATE_FORMATS``. Each candidate is then checked against the whole
    column, which is what catches a guess that only fits the first few rows.

    When several candidates read every value, the first whose dates sit on a
    regular calendar frequency wins, and the first candidate otherwise. ptype
    labels month first dates ``"date-eu"`` too, so the hint cannot settle a
    column where every value reads both ways: monthly ``"MM/01/YYYY"`` data
    read day first lands on the first twelve days of each January.

    Parameters
    ----------
    values : Any
        The column values to inspect.
    hint : str, optional
        The ptype label for this column. ``"date-eu"`` puts day first
        candidates ahead of month first ones, which decides a value like
        ``"01/02/2020"`` only when neither reading sits on a regular grid.

    Returns
    -------
    str or None
        A strptime format that parses every non-missing value, or ``None``
        when no candidate does.
    """
    import warnings  # local import

    from pandas.tseries.api import guess_datetime_format  # local import

    text = _as_clean_text(values).dropna()
    if text.empty:
        return None

    day_first = hint == "date-eu"
    sample = text.drop_duplicates().head(_SAMPLE_SIZE)

    candidates: List[str] = []
    # Trying both readings is the point, so pandas warning that a value looks
    # day first while asked month first says nothing new. Left unsuppressed it
    # fires for most columns of every upload.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        for first in (day_first, not day_first):
            for value in sample:
                try:
                    guess = guess_datetime_format(value, dayfirst=first)
                except (ValueError, TypeError):
                    guess = None
                if guess and guess not in candidates:
                    candidates.append(guess)

    extras = (
        _DAY_FIRST_EXTRA + _MONTH_FIRST_EXTRA + _YEAR_FIRST_EXTRA
        if day_first
        else EXTRA_DATE_FORMATS
    )
    candidates.extend(fmt for fmt in extras if fmt not in candidates)

    readings = []
    for candidate in candidates:
        if not _names_a_full_date(candidate):
            continue
        try:
            parsed = parse_date_column(text, candidate)
        except ValueError:
            continue
        readings.append((candidate, parsed))

    if not readings:
        return None

    for candidate, parsed in readings:
        if _lies_on_a_grid(parsed):
            return candidate
    return readings[0][0]


def infer_frequency(dates: Any) -> Union[str, "pd.Timedelta", None]:
    """Describe the calendar spacing of a parsed date series.

    Parameters
    ----------
    dates : Any
        Already parsed datetimes, in ascending order.

    Returns
    -------
    str or pandas.Timedelta or None
        A pandas frequency alias when the dates sit on a regular grid, the
        most common gap between consecutive dates when they do not, and
        ``None`` when there is too little data to say anything.
    """
    import pandas as pd  # local import

    parsed = pd.to_datetime(pd.Series(list(dates)), errors="coerce").dropna()
    if len(parsed) < 3:
        return None

    index = pd.DatetimeIndex(parsed)
    try:
        alias = pd.infer_freq(index)
    except ValueError:
        alias = None
    if alias is not None:
        return alias

    gaps = index.to_series().diff().dropna()
    modes = gaps.mode()
    return modes.iloc[0] if not modes.empty else None
