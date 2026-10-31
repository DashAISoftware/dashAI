"""The preview of a split, which the session wizard draws.

The wizard computed this itself until PR 4 of the forecasting stack: the bars
of the preview, the problems that keep it from going on, and the partitions
that receive rows, which decide the metrics a session records. Each splitter
answers for its own shape now (``BaseSplitter.preview``), and the wizard only
draws.

The arithmetic of the row splitters is the wizard's, kept as it was: the
frontend's cases (``splitPreviewCases.json``) pin that both give the same
answer. ``_js_round`` is JavaScript's ``Math.round``, which rounds halves up
where Python's ``round`` rounds them to even.

A row is ``{key, label, label_values, segments}``, each segment
``{role, fraction}`` of the dataset; an ellipsis row ``{key, ellipsis,
label, hidden_count}`` stands for rows left out. Labels, notes and errors are
``{key, values}`` the frontend translates.
"""

import math
from typing import Any, Dict, List, Optional

TRAIN = "train"
VALIDATION = "validation"
TEST = "test"
UNUSED = "unused"

PARTITIONS = (TRAIN, VALIDATION, TEST)

#: Folds or origins beyond this many are drawn as the first few, an ellipsis
#: and the last one.
MAX_DRAWN = 8
LEADING_DRAWN = 3
NOMINAL_ROWS = 100
NEGLIGIBLE = 1e-9
#: How far proportions may sum from 1 and still be taken as summing to it.
SUM_TOLERANCE = 0.0001


def empty_preview(partitions: Optional[List[str]] = None) -> Dict[str, Any]:
    """A preview with nothing to draw."""
    return {
        "rows": [],
        "notes": [],
        "shares": {},
        "errors": [],
        "partitions": list(partitions or []),
    }


def _js_round(value: float) -> int:
    return math.floor(value + 0.5)


def _number_or(value, fallback):
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    return value if is_number and math.isfinite(value) else fallback


def _clamp01(value) -> float:
    return min(1, max(0, _number_or(value, 0)))


def _segment(role: str, fraction: float) -> Dict[str, Any]:
    return {"role": role, "fraction": fraction}


def _drawable(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [piece for piece in segments if piece["fraction"] > NEGLIGIBLE]


def _row(key, label, segments, label_values=None) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "label_values": label_values or {},
        "segments": segments,
    }


def _error(key: str, **values) -> Dict[str, Any]:
    return {"key": key, "values": values}


def _rows_of(dataset) -> int:
    return max(1, _js_round(_number_or(dataset.get("total_rows"), NOMINAL_ROWS)))


def _drawn_indexes(count: int) -> List[Optional[int]]:
    if count <= MAX_DRAWN:
        return list(range(count))
    return [*range(LEADING_DRAWN), None, count - 1]


def _rows_drawn(count: int, build_row, more_label: str) -> List[Dict[str, Any]]:
    return [
        {
            "key": "ellipsis",
            "label": more_label,
            "ellipsis": True,
            "hidden_count": count - LEADING_DRAWN - 1,
        }
        if index is None
        else build_row(index)
        for index in _drawn_indexes(count)
    ]


def _shares_of(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """The share of each role in the row that stands for the split."""
    drawn = [row for row in rows if not row.get("ellipsis")]
    representative = next(
        (row for row in drawn if row["key"].startswith("fold-")),
        drawn[0] if drawn else None,
    )
    if representative is None:
        return {}

    shares: Dict[str, float] = {}
    for piece in representative["segments"]:
        shares[piece["role"]] = shares.get(piece["role"], 0) + piece["fraction"]

    reserved = next((row for row in rows if row["key"] == "reserved"), None)
    held_out = next(
        (
            piece
            for piece in (reserved or {}).get("segments", [])
            if piece["role"] == TEST
        ),
        None,
    )
    if held_out:
        shares[TEST] = held_out["fraction"]
        shares[UNUSED] = max(0, shares.get(UNUSED, 0) - held_out["fraction"])
    return shares


# Partitions: one bar of the whole dataset.


def _partition_proportions(params, dataset, split_type, indexes):
    total = _number_or(dataset.get("total_rows"), 0)
    if split_type == "predefined":
        if not total:
            return None
        return {
            TRAIN: _number_or(dataset.get("train_size"), 0) / total,
            VALIDATION: _number_or(dataset.get("val_size"), 0) / total,
            TEST: _number_or(dataset.get("test_size"), 0) / total,
        }
    if split_type == "manual":
        if not total:
            return None
        return {
            partition: len((indexes or {}).get(partition) or []) / total
            for partition in PARTITIONS
        }
    return {partition: _clamp01(params.get(partition)) for partition in PARTITIONS}


def _partition_errors(params, split_type, indexes) -> List[Dict[str, Any]]:
    if split_type == "manual":
        if not (indexes or {}).get(TRAIN):
            return [_error("trainSplitMustHaveAtLeastOneRow")]
        return []
    if split_type == "predefined":
        return []
    if params.get(TRAIN) == 0:
        return [_error("trainSplitMustBeGreaterThanZero")]
    proportions = [params.get(partition) for partition in PARTITIONS]
    are_numbers = all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in proportions
    )
    # Proportions not given yet do not sum to one either: the wizard did not
    # go on with them.
    if not are_numbers or abs(sum(proportions) - 1) >= SUM_TOLERANCE:
        return [_error("splitsMustSumToOne")]
    return []


def _partitions_with_rows(params, split_type, indexes) -> List[str]:
    if split_type in ("manual", "predefined"):
        return [
            partition
            for partition in PARTITIONS
            if len((indexes or {}).get(partition) or []) > 0
        ]
    return [
        partition
        for partition in PARTITIONS
        if _number_or(params.get(partition), 0) != 0
    ]


def partitions_preview(params, dataset, split_type, indexes) -> Dict[str, Any]:
    """Train, validation and test as shares of the whole dataset.

    Proportions that ask for more than the dataset are scaled down to it, and
    proportions that ask for less leave the rest unused.
    """
    params = params or {}
    proportions = _partition_proportions(params, dataset, split_type, indexes)
    preview = empty_preview(_partitions_with_rows(params, split_type, indexes))
    preview["errors"] = _partition_errors(params, split_type, indexes)
    if proportions is None:
        return preview

    train, validation, test = (proportions[p] for p in PARTITIONS)
    requested = train + validation + test
    scale = 1 / requested if requested > 1 else 1
    unused = 1 - requested if requested < 1 else 0
    preview["rows"] = [
        _row(
            "dataset",
            "wholeDataset",
            _drawable(
                [
                    _segment(TRAIN, train * scale),
                    _segment(VALIDATION, validation * scale),
                    _segment(TEST, test * scale),
                    _segment(UNUSED, unused),
                ]
            ),
        )
    ]
    preview["shares"] = _shares_of(preview["rows"])
    return preview


# Blocked folds: one bar per fold, and the reserved test around them.


def _reserved_row(pool, reserved):
    return _row(
        "reserved",
        "reservedTest",
        _drawable([_segment(UNUSED, pool), _segment(TEST, reserved)]),
    )


def _final_fit_row(pool, reserved):
    return _row(
        "final",
        "finalFit",
        _drawable([_segment(TRAIN, pool), _segment(TEST, reserved)]),
    )


def blocked_folds_preview(params, dataset) -> Dict[str, Any]:
    """Each fold validates on one block of the rows the test leaves.

    The reserved test proportion is carved first; the folds share the rest.
    """
    params = params or {}
    reserved = _clamp01(params.get("test_size"))
    pool = 1 - reserved
    total = _rows_of(dataset)
    pool_rows = max(1, _js_round(total * pool))
    declared = _number_or(params.get("n_splits"), None)
    fold_count = max(1, _js_round(pool_rows if declared is None else declared))
    block = pool / fold_count

    def fold_row(index):
        return _row(
            f"fold-{index}",
            "fold",
            _drawable(
                [
                    _segment(TRAIN, block * index),
                    _segment(VALIDATION, block),
                    _segment(TRAIN, block * (fold_count - index - 1)),
                    _segment(UNUSED, reserved),
                ]
            ),
            {"index": index + 1},
        )

    has_reserved = reserved > NEGLIGIBLE
    rows = [
        *([_reserved_row(pool, reserved)] if has_reserved else []),
        *_rows_drawn(fold_count, fold_row, "moreFolds"),
        *([_final_fit_row(pool, reserved)] if has_reserved else []),
    ]

    # Every fold trains and validates; the test only when rows are reserved.
    # Sessions written while the reserved proportion was still called
    # "holdout" carry that key instead.
    test_size = params.get("test_size", params.get("holdout"))
    partitions = [TRAIN, VALIDATION]
    if _number_or(test_size, 0) > 0:
        partitions.append(TEST)

    declared_folds = params.get("n_splits")
    errors = []
    if (
        isinstance(declared_folds, (int, float))
        and not isinstance(declared_folds, bool)
        and declared_folds > _number_or(dataset.get("total_rows"), 0)
    ):
        errors.append(
            _error(
                "foldsMustBeLessThanDatasetSize",
                datasetSize=dataset.get("total_rows"),
            )
        )

    return {
        "rows": rows,
        "notes": (
            [{"key": "foldsHidden", "values": {"total": fold_count}}]
            if fold_count > MAX_DRAWN
            else []
        ),
        "shares": _shares_of(rows),
        "errors": errors,
        "partitions": partitions,
    }


# Backtest origins: one bar per validation origin, the test and the kept model.


def backtest_preview(splitter, dataset) -> Dict[str, Any]:
    """Where an ``OriginSplitter`` cuts a series of ``total_rows`` steps.

    Each validation origin fits on the steps before it and forecasts the
    ``horizon`` after it; the test is one more origin, and the kept model is
    fitted on the whole series. Validation and test measure ``horizon`` steps
    each, and the history before the first origin is what is left: those are
    the shares. A series too short for the cuts is an error, with what
    the splitter needs (``OriginSplitter.needed_steps``).
    """
    n_steps = _rows_of(dataset)
    partitions = [VALIDATION, TEST]
    try:
        cuts = splitter.cuts(n_steps)
    except ValueError:
        preview = empty_preview(partitions)
        preview["errors"] = [
            _error(
                "seriesTooShort",
                needed=splitter.needed_steps(),
                rows=n_steps,
                horizon=splitter.horizon,
                origins=splitter.n_origins,
            )
        ]
        return preview

    horizon = cuts["horizon"]
    origins = cuts["validation_origins"]

    def origin_row(index):
        origin = origins[index]
        return _row(
            f"origin-{index}",
            "origin",
            _drawable(
                [
                    _segment(TRAIN, origin / n_steps),
                    _segment(VALIDATION, horizon / n_steps),
                    _segment(UNUSED, (n_steps - origin - horizon) / n_steps),
                ]
            ),
            {"index": index + 1},
        )

    test_origin = cuts["test_origin"]
    rows = [
        *_rows_drawn(len(origins), origin_row, "moreOrigins"),
        _row(
            "test",
            "testOrigin",
            _drawable(
                [
                    _segment(TRAIN, test_origin / n_steps),
                    _segment(TEST, horizon / n_steps),
                ]
            ),
        ),
        _row("final", "finalFit", [_segment(TRAIN, 1.0)]),
    ]
    return {
        "rows": rows,
        "notes": (
            [{"key": "originsHidden", "values": {"total": len(origins)}}]
            if len(origins) > MAX_DRAWN
            else []
        ),
        "shares": {
            TRAIN: origins[0] / n_steps,
            VALIDATION: horizon * len(origins) / n_steps,
            TEST: horizon / n_steps,
        },
        "errors": [],
        "partitions": partitions,
    }
