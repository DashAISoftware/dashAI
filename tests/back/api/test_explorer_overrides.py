"""Tests for explorer plot override persistence and reset."""

import json
import pathlib

from DashAI.back.core.enums.status import ExplorerStatus
from DashAI.back.dependencies.database.models import Dataset, Explorer, Notebook
from DashAI.back.exploration.artifact_store import write_artifacts

ORIGINAL_FIGURE = {
    "data": [{"y": [1, 2, 3], "type": "bar"}],
    "layout": {"title": "original"},
}
EDITED_FIGURE = {
    "data": [{"y": [1, 2, 3], "type": "bar"}],
    "layout": {"title": "edited"},
}


def _make_explorer(client, tmp_path_name="explorer_artifacts"):
    """Create a finished explorer row with one stored plotly artifact.

    Parameters
    ----------
    client : TestClient
        The app test client, used to reach the app's session factory and
        local path.
    tmp_path_name : str
        Subdirectory name under the app local path holding the artifacts.

    Returns
    -------
    tuple
        ``(explorer_id, artifacts_path)``.
    """
    services = client.app.container._services
    session_factory = services["session_factory"]
    local_path = pathlib.Path(services["config"]["LOCAL_PATH"])

    with session_factory() as db:
        dataset = Dataset(name=f"ds-{tmp_path_name}", file_path="/tmp/ds")
        db.add(dataset)
        db.commit()
        notebook = Notebook(dataset_id=dataset.id, file_path="/tmp/nb")
        db.add(notebook)
        db.commit()
        explorer = Explorer(
            notebook_id=notebook.id,
            columns=[],
            exploration_type="TestExplorer",
            parameters={},
            status=ExplorerStatus.FINISHED,
        )
        db.add(explorer)
        db.commit()
        explorer_id = explorer.id

        artifacts_path = local_path / tmp_path_name / f"{explorer_id}_artifacts.json"
        write_artifacts(
            artifacts_path,
            [
                {
                    "type": "plotly",
                    "payload": json.dumps(ORIGINAL_FIGURE),
                    "title": "Plot",
                    "role": "explanation",
                    "index": 0,
                }
            ],
        )
        explorer.artifacts_path = artifacts_path.as_posix()
        db.commit()

    return explorer_id, artifacts_path


def test_explorer_model_has_plot_overrides_column(client):
    """The explorer table stores plot overrides."""
    explorer_id, _ = _make_explorer(client, "col_check")
    session_factory = client.app.container._services["session_factory"]

    with session_factory() as db:
        explorer = db.get(Explorer, explorer_id)
        explorer.plot_overrides = {"0": json.dumps(EDITED_FIGURE)}
        db.commit()

    with session_factory() as db:
        explorer = db.get(Explorer, explorer_id)
        assert json.loads(explorer.plot_overrides["0"]) == EDITED_FIGURE
