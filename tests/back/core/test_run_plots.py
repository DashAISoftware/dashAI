"""The files that hold a run's saved plots."""

import pickle

from DashAI.back.core.artifacts import PlotlyArtifact
from DashAI.back.core.run_plots import (
    VIEWS,
    legacy_hpo_leaves,
    read_run_plot_file,
    run_plot_file,
    write_run_plot_file,
)

FIGURE = '{"data": [], "layout": {}}'


def test_the_views_are_hyperparameter_and_forecasts():
    assert VIEWS == ("hyperparameter", "forecasts")


def test_write_then_read_restamps_indexes(tmp_path):
    figure = PlotlyArtifact(payload=FIGURE, title="a")
    path = run_plot_file(tmp_path, "forecasts", "7")

    write_run_plot_file(path, [figure, figure])
    items = read_run_plot_file(path)

    assert path.name == "forecasts_plots_7.pickle"
    assert [item["index"] for item in items] == [0, 1]
    assert [item["type"] for item in items] == ["plotly", "plotly"]
    assert not path.with_suffix(".pickle.partial").exists()


def test_legacy_hpo_leaves_skips_missing_and_upgrades_strings(tmp_path):
    old = tmp_path / "history.pickle"
    old.write_bytes(pickle.dumps(FIGURE))

    leaves = legacy_hpo_leaves([str(old), None, str(tmp_path / "gone.pickle")])

    assert [leaf["type"] for leaf in leaves] == ["plotly"]
    assert leaves[0]["payload"] == FIGURE
