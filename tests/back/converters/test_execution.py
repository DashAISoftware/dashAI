import os

import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler as SkStandardScaler

from DashAI.back.converters.execution import (
    apply_session_converters,
    fit_transform_on_partition,
    fitted_converters_path,
    load_fitted_converters,
    save_fitted_converters,
    transform_for_prediction,
)
from DashAI.back.converters.imbalanced_learn.random_under_sampler_converter import (
    RandomUnderSamplerConverter,
)
from DashAI.back.converters.scikit_learn.pca import PCA
from DashAI.back.converters.scikit_learn.standard_scaler import StandardScaler
from DashAI.back.converters.simple_converters.nan_remover import NanRemover
from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.job.base_job import JobError


def _dataset(df: pd.DataFrame):
    return to_dashai_dataset(df)


def _registry(*classes):
    """Minimal stand-in for ComponentRegistry: only supports `[name]["class"]`."""
    return {cls.__name__: {"class": cls} for cls in classes}


def _converter_config(name, params=None, columns=None):
    return {"converter": name, "params": params or {}, "columns": columns or []}


def test_fit_uses_only_train_rows_not_test():
    """The scaler's learned mean/std must come from train alone, and the same
    fitted instance (not a re-fit) must be used to transform test."""
    x_train = _dataset(pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]}))
    y_train = _dataset(pd.DataFrame({"target": [0, 1, 0, 1]}))
    # test has a very different distribution; if the scaler leaked into it,
    # the transformed values below would not match a train-only fit.
    x_test = _dataset(pd.DataFrame({"a": [100.0, 200.0]}))

    registry = _registry(StandardScaler)
    config = [_converter_config("StandardScaler")]

    new_x_train, new_y_train, x_others, fitted = fit_transform_on_partition(
        config, registry, x_train, y_train, x_others={"test": x_test}
    )

    expected = SkStandardScaler().fit(pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]}))

    assert new_x_train.to_pandas()["a"].tolist() == pytest.approx(
        expected.transform(pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]})).ravel().tolist()
    )
    # test transformed using train's mean/std, not its own.
    assert x_others["test"].to_pandas()["a"].tolist() == pytest.approx(
        expected.transform(pd.DataFrame({"a": [100.0, 200.0]})).ravel().tolist()
    )
    # y is untouched by a non-sampler converter.
    assert new_y_train.to_pandas()["target"].tolist() == [0, 1, 0, 1]
    # the fitted StandardScaler instance is captured for prediction-time reuse.
    assert len(fitted) == 1
    assert fitted[0]["columns"] == ["a"]
    assert fitted[0]["instance"].transform(
        _dataset(pd.DataFrame({"a": [100.0, 200.0]}))
    ).to_pandas()["a"].tolist() == pytest.approx(
        expected.transform(pd.DataFrame({"a": [100.0, 200.0]})).ravel().tolist()
    )


def test_partial_column_scope_leaves_other_columns_untouched():
    x_train = _dataset(pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]}))
    y_train = _dataset(pd.DataFrame({"target": [0, 1, 0]}))
    x_test = _dataset(pd.DataFrame({"a": [5.0], "b": [50.0]}))

    registry = _registry(StandardScaler)
    config = [_converter_config("StandardScaler", columns=["a"])]

    new_x_train, _, x_others, _ = fit_transform_on_partition(
        config, registry, x_train, y_train, x_others={"test": x_test}
    )

    assert new_x_train.to_pandas()["b"].tolist() == [10.0, 20.0, 30.0]
    assert x_others["test"].to_pandas()["b"].tolist() == [50.0]
    # column "a" did change (scaled).
    assert new_x_train.to_pandas()["a"].tolist() != [1.0, 2.0, 3.0]


def test_sampler_only_changes_train_not_test_or_validation():
    # 15 majority (class 0) + 5 minority (class 1) rows.
    df_x = pd.DataFrame({"a": list(range(20))})
    df_y = pd.DataFrame({"target": [0] * 15 + [1] * 5})
    x_train = _dataset(df_x)
    y_train = _dataset(df_y)
    x_validation = _dataset(pd.DataFrame({"a": [999.0]}))
    x_test = _dataset(pd.DataFrame({"a": [888.0]}))

    registry = _registry(RandomUnderSamplerConverter)
    config = [
        _converter_config(
            "RandomUnderSamplerConverter",
            params={"sampling_strategy": "auto", "random_state": 0},
        )
    ]

    new_x_train, new_y_train, x_others, fitted = fit_transform_on_partition(
        config,
        registry,
        x_train,
        y_train,
        x_others={"validation": x_validation, "test": x_test},
    )

    # Majority class down-sampled to match the minority class (5 and 5).
    assert len(new_x_train) == 10
    assert len(new_y_train) == 10
    # validation/test are completely unaffected by the resampling.
    assert x_others["validation"].to_pandas()["a"].tolist() == [999.0]
    assert x_others["test"].to_pandas()["a"].tolist() == [888.0]
    # samplers are never captured for prediction-time replay.
    assert fitted == []


def test_nan_remover_keeps_x_and_y_aligned_and_merged():
    """Regression test: NanRemover changes the row count (CHANGES_ROW_COUNT),
    so `fit_transform_on_partition` feeds it x_train/y_train and expects a
    combined dataset back to split apart again (same contract as samplers).
    NanRemover.transform used to ignore `y` entirely, so the output column
    was silently dropped and the follow-up split blew up with a KeyError."""
    x_train = _dataset(pd.DataFrame({"a": [1.0, None, 3.0, 4.0]}))
    y_train = _dataset(pd.DataFrame({"target": [0, 1, 0, 1]}))
    x_test = _dataset(pd.DataFrame({"a": [999.0]}))

    registry = _registry(NanRemover)
    config = [_converter_config("NanRemover")]

    new_x_train, new_y_train, x_others, fitted = fit_transform_on_partition(
        config, registry, x_train, y_train, x_others={"test": x_test}
    )

    # the row with a NaN in "a" is dropped from both x and y, in sync.
    assert new_x_train.to_pandas()["a"].tolist() == [1.0, 3.0, 4.0]
    assert new_y_train.to_pandas()["target"].tolist() == [0, 0, 1]
    # test is left untouched, like any other row-count-changing converter.
    assert x_others["test"].to_pandas()["a"].tolist() == [999.0]
    assert fitted == []


def test_empty_other_partition_is_skipped():
    """The CV 'full_dataset' fold has an empty test partition; it must not
    be transformed (there is nothing to transform, and no error raised)."""
    x_train = _dataset(pd.DataFrame({"a": [1.0, 2.0, 3.0]}))
    y_train = _dataset(pd.DataFrame({"target": [0, 1, 0]}))
    empty_x = _dataset(pd.DataFrame({"a": []}))

    registry = _registry(StandardScaler)
    config = [_converter_config("StandardScaler")]

    _, _, x_others, _ = fit_transform_on_partition(
        config, registry, x_train, y_train, x_others={"test": empty_x}
    )
    assert len(x_others["test"]) == 0


def test_fit_failure_raises_joberror_with_context():
    x_train = _dataset(pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]}))
    y_train = _dataset(pd.DataFrame({"target": [0, 1]}))

    registry = _registry(PCA)
    # n_components > number of features/rows available: sklearn raises.
    config = [_converter_config("PCA", params={"n_components": 5})]

    with pytest.raises(JobError, match="PCA"):
        fit_transform_on_partition(
            config, registry, x_train, y_train, x_others={}, partition_label="fold_0"
        )


def test_apply_session_converters_holdout_shape():
    x = {
        "train": _dataset(pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]})),
        "validation": _dataset(pd.DataFrame({"a": [5.0]})),
        "test": _dataset(pd.DataFrame({"a": [6.0]})),
    }
    y = {
        "train": _dataset(pd.DataFrame({"target": [0, 1, 0, 1]})),
        "validation": _dataset(pd.DataFrame({"target": [0]})),
        "test": _dataset(pd.DataFrame({"target": [1]})),
    }

    registry = _registry(StandardScaler)
    config = [_converter_config("StandardScaler")]

    new_x, new_y, fitted = apply_session_converters(x, y, config, registry)

    assert set(new_x.keys()) == {"train", "validation", "test"}
    assert len(new_x["train"]) == 4
    assert len(new_x["validation"]) == 1
    assert len(new_y["validation"]) == 1
    # holdout has a single train partition, so its fit is "the" final fit.
    assert len(fitted) == 1


def test_cv_non_supervised_converter_fits_once_and_matches_across_folds():
    """A non-supervised, non-row-changing converter (StandardScaler here,
    standing in for anything data-dependent like a text vectorizer) must
    produce IDENTICAL fitted parameters across every fold — because it's
    fit once on full_dataset and reused via transform(), never refit per
    fold. Different train subsets would normally give different mean/std;
    identical values across folds is the signal the fix is working."""
    fold_0 = {
        "train": _dataset(pd.DataFrame({"a": [1.0, 2.0, 3.0]})),
        "test": _dataset(pd.DataFrame({"a": [10.0]})),
    }
    fold_1 = {
        "train": _dataset(pd.DataFrame({"a": [100.0, 200.0, 300.0]})),
        "test": _dataset(pd.DataFrame({"a": [150.0]})),
    }
    full_dataset = {
        "train": _dataset(pd.DataFrame({"a": [1.0, 2.0, 3.0, 100.0, 200.0, 300.0]})),
        "test": _dataset(pd.DataFrame({"a": []})),
    }
    y_fold_0 = {
        "train": _dataset(pd.DataFrame({"target": [0, 1, 0]})),
        "test": _dataset(pd.DataFrame({"target": [1]})),
    }
    y_fold_1 = {
        "train": _dataset(pd.DataFrame({"target": [0, 1, 0]})),
        "test": _dataset(pd.DataFrame({"target": [1]})),
    }
    y_full_dataset = {
        "train": _dataset(pd.DataFrame({"target": [0, 1, 0, 0, 1, 0]})),
        "test": _dataset(pd.DataFrame({"target": []})),
    }

    x = [fold_0, fold_1, full_dataset]
    y = [y_fold_0, y_fold_1, y_full_dataset]

    registry = _registry(StandardScaler)
    config = [_converter_config("StandardScaler")]

    new_x, _, fitted = apply_session_converters(x, y, config, registry)

    # Fit only on full_dataset's train (all 6 rows) — same expected
    # transform everywhere, including fold_0/fold_1's own test partitions.
    full_expected = SkStandardScaler().fit(
        pd.DataFrame({"a": [1.0, 2.0, 3.0, 100.0, 200.0, 300.0]})
    )

    fold_0_transformed_test = new_x[0]["test"].to_pandas()["a"].tolist()
    fold_1_transformed_test = new_x[1]["test"].to_pandas()["a"].tolist()

    assert fold_0_transformed_test == pytest.approx(
        full_expected.transform(pd.DataFrame({"a": [10.0]})).ravel().tolist()
    )
    assert fold_1_transformed_test == pytest.approx(
        full_expected.transform(pd.DataFrame({"a": [150.0]})).ravel().tolist()
    )
    # fold_0's own train, transformed with the SAME (full_dataset-fitted)
    # scaler — NOT what an independent per-fold fit on [1,2,3] would give.
    fold_0_train_transformed = new_x[0]["train"].to_pandas()["a"].tolist()
    assert fold_0_train_transformed == pytest.approx(
        full_expected.transform(pd.DataFrame({"a": [1.0, 2.0, 3.0]})).ravel().tolist()
    )

    # full_dataset (last entry) fit on the whole dataset; its empty test
    # partition is left alone (no error, still empty).
    assert len(new_x[2]["test"]) == 0
    assert new_x[2]["train"].to_pandas()["a"].tolist() == pytest.approx(
        full_expected.transform(
            pd.DataFrame({"a": [1.0, 2.0, 3.0, 100.0, 200.0, 300.0]})
        )
        .ravel()
        .tolist()
    )
    # the fitted converters returned are the full_dataset fold's fit.
    assert len(fitted) == 1
    assert fitted[0]["instance"].transform(
        _dataset(pd.DataFrame({"a": [1.0, 2.0, 3.0, 100.0, 200.0, 300.0]}))
    ).to_pandas()["a"].tolist() == pytest.approx(
        full_expected.transform(
            pd.DataFrame({"a": [1.0, 2.0, 3.0, 100.0, 200.0, 300.0]})
        )
        .ravel()
        .tolist()
    )


def test_cv_supervised_converter_still_fits_independently_per_fold():
    """Unchanged-behavior guard: a SUPERVISED converter (sampler here) must
    keep fitting independently per fold — this must NOT be swept into the
    fit-once path, since that would leak target information across folds."""
    df_x = pd.DataFrame({"a": list(range(20))})
    df_y = pd.DataFrame({"target": [0] * 15 + [1] * 5})
    fold_0 = {"train": _dataset(df_x), "test": _dataset(pd.DataFrame({"a": [999.0]}))}
    full_dataset = {"train": _dataset(df_x), "test": _dataset(pd.DataFrame({"a": []}))}
    y_fold_0 = {
        "train": _dataset(df_y),
        "test": _dataset(pd.DataFrame({"target": [1]})),
    }
    y_full_dataset = {
        "train": _dataset(df_y),
        "test": _dataset(pd.DataFrame({"target": []})),
    }

    x = [fold_0, full_dataset]
    y = [y_fold_0, y_full_dataset]

    registry = _registry(RandomUnderSamplerConverter)
    config = [
        _converter_config(
            "RandomUnderSamplerConverter",
            params={"sampling_strategy": "auto", "random_state": 0},
        )
    ]

    new_x, new_y, fitted = apply_session_converters(x, y, config, registry)

    # Both folds independently resampled the SAME 20-row input to 10 rows —
    # the real guard is that x_others (test) stayed untouched, same as
    # before this change (samplers never touch validation/test).
    assert len(new_x[0]["train"]) == 10
    assert len(new_x[1]["train"]) == 10
    assert new_x[0]["test"].to_pandas()["a"].tolist() == [999.0]
    assert fitted == []  # samplers are never kept for prediction-time replay


def test_cv_non_supervised_row_changing_converter_still_fits_per_fold():
    """A non-supervised converter that changes row count (NanRemover) is
    NOT swept into the fit-once path either — only fit_transform_on_partition's
    existing CHANGES_ROW_COUNT handling (train-only, x_others untouched)
    applies, same as it always has. NanRemover's own fit doesn't depend on
    row content (only column names/types), so per-fold independent fits
    already produce identical columns everywhere — no consistency problem
    to solve here in the first place."""
    fold_0 = {
        "train": _dataset(pd.DataFrame({"a": [1.0, None, 3.0]})),
        "test": _dataset(pd.DataFrame({"a": [10.0]})),
    }
    full_dataset = {
        "train": _dataset(pd.DataFrame({"a": [1.0, None, 3.0, 4.0, None]})),
        "test": _dataset(pd.DataFrame({"a": []})),
    }
    y_fold_0 = {
        "train": _dataset(pd.DataFrame({"target": [0, 1, 0]})),
        "test": _dataset(pd.DataFrame({"target": [1]})),
    }
    y_full_dataset = {
        "train": _dataset(pd.DataFrame({"target": [0, 1, 0, 1, 0]})),
        "test": _dataset(pd.DataFrame({"target": []})),
    }

    x = [fold_0, full_dataset]
    y = [y_fold_0, y_full_dataset]

    registry = _registry(NanRemover)
    config = [_converter_config("NanRemover")]

    new_x, new_y, _ = apply_session_converters(x, y, config, registry)

    # fold_0's own 1 NaN row dropped from its own 3-row train -> 2 rows.
    assert len(new_x[0]["train"]) == 2
    # full_dataset's own 2 NaN rows dropped from its own 5-row train -> 3.
    assert len(new_x[1]["train"]) == 3
    # test partitions untouched, as CHANGES_ROW_COUNT converters always do.
    assert len(new_x[0]["test"]) == 1


def test_apply_session_converters_noop_without_config():
    x = {"train": _dataset(pd.DataFrame({"a": [1.0]}))}
    y = {"train": _dataset(pd.DataFrame({"target": [0]}))}
    new_x, new_y, fitted = apply_session_converters(x, y, [], {})
    assert new_x is x
    assert new_y is y
    assert fitted == []


def test_save_load_and_transform_for_prediction_round_trip(tmp_path):
    """The full prediction-time story: fit on train, save to disk next to a
    (fake) model path, load it back, and replay it on brand-new data."""
    x_train = _dataset(pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]}))
    y_train = _dataset(pd.DataFrame({"target": [0, 1, 0, 1]}))

    registry = _registry(StandardScaler)
    config = [_converter_config("StandardScaler")]

    _, _, _, fitted = fit_transform_on_partition(config, registry, x_train, y_train)

    run_path = str(tmp_path / "42")  # sklearn-style: a plain file path, no dir.
    saved_path = save_fitted_converters(run_path, fitted)
    assert saved_path == f"{run_path}_converters.pkl"
    assert os.path.exists(saved_path)

    loaded = load_fitted_converters(run_path)
    assert len(loaded) == 1

    new_input = _dataset(pd.DataFrame({"a": [100.0, 200.0]}))
    transformed = transform_for_prediction(new_input, loaded)

    expected = SkStandardScaler().fit(pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]}))
    assert transformed.to_pandas()["a"].tolist() == pytest.approx(
        expected.transform(pd.DataFrame({"a": [100.0, 200.0]})).ravel().tolist()
    )


def test_save_fitted_converters_noop_when_empty(tmp_path):
    run_path = str(tmp_path / "42")
    assert save_fitted_converters(run_path, []) is None
    assert not os.path.exists(fitted_converters_path(run_path))


def test_load_fitted_converters_missing_file_returns_empty(tmp_path):
    run_path = str(tmp_path / "does-not-exist")
    assert load_fitted_converters(run_path) == []


def test_transform_for_prediction_skips_samplers_by_construction():
    """Samplers never end up in `fitted_converters` (see
    test_sampler_only_changes_train_not_test_or_validation), so replaying an
    empty list on new prediction input is simply a no-op."""
    new_input = _dataset(pd.DataFrame({"a": [1.0, 2.0]}))
    result = transform_for_prediction(new_input, [])
    assert result.to_pandas()["a"].tolist() == [1.0, 2.0]
