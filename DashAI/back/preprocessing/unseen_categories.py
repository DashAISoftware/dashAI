"""The record of the categories a prediction met that training never saw.

Encoders treat a category unseen in fit instead of failing: a session encoder
by default, a model's own encoders always. Treating it silently would hide
that the model is predicting on something it never learnt, so whoever treats
one reports it with ``unseen_record``, and the prediction keeps the records.
"""

from typing import TYPE_CHECKING, Any, Dict, Iterable, List

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

#: How many unseen values a record keeps. The count says how many there were.
SAMPLE_SIZE = 20

#: How many unseen values a message lists before it only counts the rest.
SHOWN_IN_MESSAGE = 10


def unseen_message(
    label: str, hint: str, column: str, values: List[str], where: str
) -> str:
    """The error of an encoder set to raise on a category it did not see.

    Parameters
    ----------
    label : str
        How the encoder is named to the user: a session step
        ("OneHotEncoder (step 1)") or a notebook converter ("OneHotEncoder").
    hint : str
        What to change so the encoder treats them (its ``UNKNOWN_HINT``).
    column : str
        The column the values came in.
    values : list of str
        The unseen values, sorted.
    where : str
        Where the values were met, completing "values of column 'c' that ...".
    """
    shown = ", ".join(repr(value) for value in values[:SHOWN_IN_MESSAGE])
    if len(values) > SHOWN_IN_MESSAGE:
        shown += f" and {len(values) - SHOWN_IN_MESSAGE} more"
    return (
        f"{label} cannot encode values of column '{column}' that {where}: "
        f"{shown}. It is set to raise on unknown categories; {hint}."
    )


def check_unseen(
    converter: Any, x: "DashAIDataset", label: str, where: str
) -> Dict[str, List[str]]:
    """The categories of ``x`` a fitted encoder did not see, or its error.

    An encoder set to raise on them raises here instead of in ``transform``,
    with a message that names the encoder, the column and the values, rather
    than letting sklearn name the column by its position.

    Parameters
    ----------
    converter : BaseConverter
        A fitted converter. One that is not an encoder sees everything.
    x : DashAIDataset
        The rows it is about to transform, with its scope's columns.
    label, where : str
        As ``unseen_message`` takes them.

    Returns
    -------
    dict
        Column name to its unseen values, for an encoder that treats them.

    Raises
    ------
    ValueError
        If the encoder is set to raise and ``x`` has a category it did not
        see; the first such column is named.
    """
    unseen_values = getattr(converter, "unseen_values", None)
    if unseen_values is None or x.num_rows == 0:
        return {}
    unseen = unseen_values(x)
    if unseen and converter.raises_on_unseen():
        column, values = next(iter(unseen.items()))
        raise ValueError(
            unseen_message(label, type(converter).UNKNOWN_HINT, column, values, where)
        )
    return unseen


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
