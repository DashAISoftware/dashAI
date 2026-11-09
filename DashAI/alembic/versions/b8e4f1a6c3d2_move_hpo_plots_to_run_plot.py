"""move the HPO plot paths of a run into run_plot rows

Revision ID: b8e4f1a6c3d2
Revises: a7d3e9c2b4f1
Create Date: 2026-11-09 12:30:00.000000

A run kept one pickle per hyperparameter plot, named by four columns. Each
run's pickles are combined, in column order, into one file holding the list
of their artifacts, a ``hyperparameter`` row points at it, and the old
pickles and columns go. A run whose pickles are all gone gets no row.

The downgrade brings the columns back empty: the plots stay in the
``run_plot`` files, which the previous revision drops with the table.
"""

import os
import pickle
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e4f1a6c3d2"
down_revision: Union[str, None] = "a7d3e9c2b4f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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


def move_legacy_plots(connection) -> None:
    """Combine every run's HPO pickles into one file and a run_plot row."""
    runs = connection.execute(
        sa.text(f"SELECT id, {', '.join(PLOT_COLUMNS)} FROM run")
    ).all()
    for run_id, *paths in runs:
        found = [path for path in paths if path and os.path.isfile(path)]
        if not found:
            continue
        leaves = []
        for path in found:
            with open(path, "rb") as file:
                leaf = _leaf(pickle.load(file))
            if leaf is not None:
                leaves.append(leaf)
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
        for path in found:
            os.remove(path)


def upgrade() -> None:
    move_legacy_plots(op.get_bind())
    with op.batch_alter_table("run", schema=None) as batch_op:
        for column in PLOT_COLUMNS:
            batch_op.drop_column(column)


def downgrade() -> None:
    with op.batch_alter_table("run", schema=None) as batch_op:
        for column in PLOT_COLUMNS:
            batch_op.add_column(sa.Column(column, sa.String(), nullable=True))
