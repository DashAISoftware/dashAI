"""The record of the categories a prediction met that training never saw.

Encoders treat a category unseen in fit instead of failing: a session encoder
by default, a model's own encoders always. Treating it silently would hide
that the model is predicting on something it never learnt, so whoever treats
one reports it with ``unseen_record``, and the prediction keeps the records.
"""

from typing import Any, Dict, Iterable, List

#: How many unseen values a record keeps. The count says how many there were.
SAMPLE_SIZE = 20


def unseen_record(source: str, column: str, values: Iterable[Any]) -> Dict:
    """One encoder's unseen values in one column, as a prediction keeps them.

    Parameters
    ----------
    source : str
        What treated the values: a session step ("OneHotEncoder (step 1)")
        or a model ("RandomForestClassifier (model)").
    column : str
        The column the values came in.
    values : iterable
        The distinct values the encoder did not see.

    Returns
    -------
    dict
        ``source``, ``column``, ``values`` (the first ``SAMPLE_SIZE`` as
        sorted strings) and ``count`` (how many there were).
    """
    ordered: List[str] = sorted({str(value) for value in values})
    return {
        "source": source,
        "column": column,
        "values": ordered[:SAMPLE_SIZE],
        "count": len(ordered),
    }
