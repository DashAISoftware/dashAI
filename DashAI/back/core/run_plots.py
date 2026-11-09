"""Where a run's saved plots live, and how they are written and read.

A run keeps one file per plot view it has (``VIEWS``): the normalized
artifact list of that view, pickled. The ``run_plot`` table points at it and
keeps the user's edits beside it.
"""

import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from DashAI.back.core.artifacts import normalize_artifacts

VIEWS = ("hyperparameter", "forecasts")


def run_plot_file(runs_path: Union[str, Path], view: str, run_key: str) -> Path:
    """Where the plots of one view of a run are kept.

    Parameters
    ----------
    runs_path : str or Path
        The runs directory.
    view : str
        One of ``VIEWS``.
    run_key : str
        What names the run's files: its id, or the artifact prefix a caller
        that is not a run passes.

    Returns
    -------
    Path
        ``<runs_path>/<view>_plots_<run_key>.pickle``.
    """
    return Path(runs_path) / f"{view}_plots_{run_key}.pickle"


def write_run_plot_file(path: Path, items: List[Any]) -> None:
    """Pickle the normalized artifacts of a view, written aside then moved.

    Parameters
    ----------
    path : Path
        Where to write, as ``run_plot_file`` names it.
    items : list
        Artifacts, grouped artifacts or their wire dicts.
    """
    path = Path(path)
    partial = path.with_suffix(".pickle.partial")
    with open(partial, "wb") as file:
        pickle.dump(normalize_artifacts(items), file)
    os.replace(partial, path)


def read_run_plot_file(path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Read the artifacts of a view, normalized again on the way out.

    Parameters
    ----------
    path : str or Path
        The file ``write_run_plot_file`` wrote.

    Returns
    -------
    list of dict
        The artifact wire dicts, every leaf stamped with its ``index``.

    Raises
    ------
    FileNotFoundError
        If the file is gone.
    """
    with open(path, "rb") as file:
        return normalize_artifacts(pickle.load(file))


def legacy_hpo_leaves(paths: Sequence[Optional[str]]) -> List[Dict[str, Any]]:
    """The leaves of the per-plot HPO pickles a run kept before ``run_plot``.

    Parameters
    ----------
    paths : sequence of str or None
        The old pickle paths in their column order; unset or missing ones are
        skipped.

    Returns
    -------
    list of dict
        One artifact wire dict per plot found, plain plotly JSON strings
        upgraded to typed artifacts.
    """
    leaves: List[Dict[str, Any]] = []
    for path in paths:
        if not path or not os.path.exists(path):
            continue
        with open(path, "rb") as file:
            leaves.extend(normalize_artifacts(pickle.load(file)))
    return leaves
