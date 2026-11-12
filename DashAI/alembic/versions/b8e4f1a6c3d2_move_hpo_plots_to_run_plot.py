"""move the HPO plot paths of a run into run_plot rows

Revision ID: b8e4f1a6c3d2
Revises: a7d3e9c2b4f1
Create Date: 2026-11-09 12:30:00.000000

A run kept one pickle per hyperparameter plot, named by four columns. Each
run's pickles are combined, in column order, into one file holding the list
of their artifacts, a ``hyperparameter`` row points at it, and the old
pickles and columns go. A pickle that is gone or cannot be read (one cut
short by a save that died) is skipped, and a run with none left gets no
row. The old pickles are removed only once the columns are dropped, so a
failed upgrade keeps them.

The downgrade brings the columns back empty: the plots stay in the
``run_plot`` files, which the previous revision drops with the table.
"""

import logging
import os
import pickle
from typing import List, Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e4f1a6c3d2"
down_revision: Union[str, None] = "a7d3e9c2b4f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger(__name__)

PLOT_COLUMNS = (
    "plot_history_path",
    "plot_slice_path",
    "plot_contour_path",
    "plot_importance_path",
)


def _leaf(value) -> dict:
    """One saved plot as an artifact dict, whatever shape it was pickled in."""
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, str):
        return {"type": "plotly", "payload": value, "title": None}
    return value


def _read_leaf(path: str) -> Optional[dict]:
    """The plot a pickle holds, or ``None`` when it cannot be read."""
    try:
        with open(path, "rb") as file:
            return _leaf(pickle.load(file))
    except Exception as e:
        log.warning(f"Skipping the unreadable plot {path}: {e}")
        return None


def move_legacy_plots(connection) -> List[str]:
    """Combine every run's HPO pickles into one file and a run_plot row.

    Returns
    -------
    list of str
        The old pickles that were moved, for the caller to remove once the
        columns are dropped.
    """
    runs = connection.execute(
        sa.text(f"SELECT id, {', '.join(PLOT_COLUMNS)} FROM run")
    ).all()
    moved: List[str] = []
    for run_id, *paths in runs:
        found = [path for path in paths if path and os.path.isfile(path)]
        read = [(path, _read_leaf(path)) for path in found]
        leaves = [leaf for _, leaf in read if leaf is not None]
        if not leaves:
            continue
        target = os.path.join(
            os.path.dirname(found[0]), f"hyperparameter_plots_{run_id}.pickle"
        )
        with open(target, "wb") as file:
            pickle.dump(leaves, file)
        connection.execute(
            sa.text(
                "INSERT INTO run_plot (run_id, view, artifacts_path) "
                "VALUES (:run_id, 'hyperparameter', :path)"
            ),
            {"run_id": run_id, "path": target},
        )
        moved += [path for path, leaf in read if leaf is not None]
    return moved


def upgrade() -> None:
    moved = move_legacy_plots(op.get_bind())
    with op.batch_alter_table("run", schema=None) as batch_op:
        for column in PLOT_COLUMNS:
            batch_op.drop_column(column)
    for path in moved:
        try:
            os.remove(path)
        except OSError as e:
            log.warning(f"Could not remove the moved plot {path}: {e}")


def downgrade() -> None:
    with op.batch_alter_table("run", schema=None) as batch_op:
        for column in PLOT_COLUMNS:
            batch_op.add_column(sa.Column(column, sa.String(), nullable=True))
