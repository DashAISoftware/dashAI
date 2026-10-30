"""The split preview, computed by the splitter, on the frontend's own cases.

The session wizard used to compute the preview of a split, the problems that
keep it from going on and the partitions that receive rows, with arithmetic of
its own. ``splitPreviewCases.json`` recorded what it computed; the splitters
have to answer the same, so moving the arithmetic changes nothing for the
splitters of rows.

A backtest's preview is new: its cases live here.
"""

import json
from pathlib import Path

import pytest

from DashAI.back.splitters.fold_splitter import FoldSplitter
from DashAI.back.splitters.holdout import HoldoutSplitter
from DashAI.back.splitters.rolling_origin import RollingOriginSplitter
from DashAI.back.splitters.temporal_holdout import TemporalHoldoutSplitter

CASES_PATH = (
    Path(__file__).parents[3]
    / "DashAI"
    / "front"
    / "src"
    / "components"
    / "models"
    / "modelSession"
    / "__fixtures__"
    / "splitPreviewCases.json"
)
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))

SPLITTERS = {"partitions": HoldoutSplitter, "blocked_folds": FoldSplitter}


def _close(actual, expected):
    """Equal, with the floats compared to the last bits."""
    if isinstance(expected, float):
        return actual == pytest.approx(expected, rel=1e-12, abs=1e-15)
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _close(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _close(a, e) for a, e in zip(actual, expected, strict=True)
        )
    return actual == expected


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_a_splitter_of_rows_previews_what_the_wizard_drew(case):
    splitter = SPLITTERS[case["geometry"]]

    preview = splitter.preview(
        case["params"], case["dataset"], case["split_type"], case["indexes"]
    )

    for key in ("rows", "notes", "shares", "errors", "partitions"):
        assert _close(preview[key], case["expected"][key]), key


def test_a_splitter_without_a_preview_says_so():
    from DashAI.back.splitters.base_splitter import BaseSplitter

    assert BaseSplitter.preview({}, {"total_rows": 10}) is None


def _origins(splitter, params, n_rows):
    return splitter.preview(params, {"total_rows": n_rows})


def test_a_backtest_previews_one_row_per_origin_and_the_test():
    preview = _origins(RollingOriginSplitter, {"horizon": 6, "n_origins": 3}, 48)

    assert [row["key"] for row in preview["rows"]] == [
        "origin-0",
        "origin-1",
        "origin-2",
        "test",
        "final",
    ]
    # Origin 24 fits [0, 24) and forecasts [24, 30); the rest is not used.
    assert preview["rows"][0]["label"] == "origin"
    assert preview["rows"][0]["label_values"] == {"index": 1}
    assert preview["rows"][0]["segments"] == [
        {"role": "train", "fraction": 24 / 48},
        {"role": "validation", "fraction": 6 / 48},
        {"role": "unused", "fraction": 18 / 48},
    ]
    # The last validation window ends where the test starts.
    assert preview["rows"][2]["segments"] == [
        {"role": "train", "fraction": 36 / 48},
        {"role": "validation", "fraction": 6 / 48},
        {"role": "unused", "fraction": 6 / 48},
    ]
    assert preview["rows"][3] == {
        "key": "test",
        "label": "testOrigin",
        "label_values": {},
        "segments": [
            {"role": "train", "fraction": 42 / 48},
            {"role": "test", "fraction": 6 / 48},
        ],
    }
    # The kept model is fitted on the whole series.
    assert preview["rows"][4]["segments"] == [{"role": "train", "fraction": 1.0}]


def test_a_backtest_shares_are_the_history_the_validation_and_the_test():
    preview = _origins(RollingOriginSplitter, {"horizon": 6, "n_origins": 3}, 48)

    # Validation and test measure h steps each; the history is what is left.
    assert preview["shares"] == {
        "train": 24 / 48,
        "validation": 18 / 48,
        "test": 6 / 48,
    }
    assert preview["errors"] == []
    assert preview["notes"] == []
    assert preview["partitions"] == ["validation", "test"]


def test_a_temporal_holdout_previews_a_single_origin():
    preview = _origins(TemporalHoldoutSplitter, {"horizon": 3}, 24)

    assert [row["key"] for row in preview["rows"]] == ["origin-0", "test", "final"]
    assert preview["shares"] == {"train": 18 / 24, "validation": 3 / 24, "test": 3 / 24}


def test_a_series_too_short_for_the_cuts_is_an_error_of_the_preview():
    preview = _origins(RollingOriginSplitter, {"horizon": 6, "n_origins": 3}, 24)

    assert preview["rows"] == []
    assert preview["errors"] == [
        {
            "key": "seriesTooShort",
            "values": {"needed": 25, "rows": 24, "horizon": 6, "origins": 3},
        }
    ]


def test_more_origins_than_are_drawn_leave_a_note():
    preview = _origins(RollingOriginSplitter, {"horizon": 1, "n_origins": 12}, 48)

    keys = [row["key"] for row in preview["rows"]]
    assert keys == [
        "origin-0",
        "origin-1",
        "origin-2",
        "ellipsis",
        "origin-11",
        "test",
        "final",
    ]
    assert preview["rows"][3] == {
        "key": "ellipsis",
        "label": "moreOrigins",
        "ellipsis": True,
        "hidden_count": 8,
    }
    assert preview["notes"] == [{"key": "originsHidden", "values": {"total": 12}}]


def test_proportions_not_given_yet_keep_the_wizard_from_going_on():
    # The wizard did not go on while the form had not given the three
    # proportions; it said nothing either, since the form fills them at once.
    preview = HoldoutSplitter.preview({}, {"total_rows": 10}, "random")

    assert preview["errors"] == [{"key": "splitsMustSumToOne", "values": {}}]
    assert preview["partitions"] == []
