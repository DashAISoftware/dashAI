"""Unit tests for the per-run benchmark output directory layout.

Tests cover ``RAG_benchmark/app/output.py`` (run directory creation
and the ``config.json`` writers), the ``BenchmarkLogger`` incremental
output, and the recursive status scan used by ``--skip-passes``. No model
downloads or API keys are required.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

from RAG_benchmark.app.benchmark_utils import (
    BenchmarkLogger,
    BenchmarkResult,
    load_last_run_statuses,
)
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.output import (
    create_run_directory,
    update_run_config,
    write_run_config,
)

_COMPONENT_CSV_HEADER = (
    "id,timestamp,component_type,component_class,model_name,config_name,"
    "status,time_seconds,first_load_time,error_message\n"
)


def test_create_run_directory_builds_layout(tmp_path: Path) -> None:
    """A run directory gets the expected folders and run_id."""
    run_dir = create_run_directory(tmp_path, datetime(2026, 8, 2, 14, 35, 0))

    assert run_dir.root == tmp_path / "20260802_143500"
    assert run_dir.components_dir == tmp_path / "20260802_143500" / "components"
    assert run_dir.pipelines_dir == tmp_path / "20260802_143500" / "pipelines"
    assert run_dir.components_dir.exists()
    assert run_dir.pipelines_dir.exists()
    assert run_dir.run_id == "20260802_143500"


def test_create_run_directory_avoids_collision(tmp_path: Path) -> None:
    """Two runs at the same time get a suffixed second folder."""
    create_run_directory(tmp_path, datetime(2026, 8, 2, 14, 35, 0))
    second = create_run_directory(tmp_path, datetime(2026, 8, 2, 14, 35, 0))

    assert second.root == tmp_path / "20260802_143500_2"
    assert second.run_id == "20260802_143500_2"
    assert second.components_dir.exists()
    assert second.pipelines_dir.exists()


def test_benchmark_logger_writes_new_layout(tmp_path: Path) -> None:
    """BenchmarkLogger writes results.csv, configs.json and io.json keyed by id."""
    logger = BenchmarkLogger(tmp_path)
    config = {"component_class": "ClassA", "config_name": "cfg", "params": {}}
    inputs = {"config": config, "component_type": "chunker"}
    outputs = {
        "status": "passed",
        "time_seconds": 1.0,
        "first_load_time": 0.5,
        "error_message": "",
        "output_size": None,
    }

    result_id = logger.log(
        BenchmarkResult(
            component_type="chunker",
            component_class="ClassA",
            model_name="ModelX",
            config_name="cfg",
            params={},
            status="passed",
            time_seconds=1.0,
            first_load_time=0.5,
            error_message="",
            timestamp="2026-08-02T14:35:00",
        ),
        config=config,
        inputs=inputs,
        outputs=outputs,
    )

    assert result_id == "0001"
    assert (tmp_path / "results.csv").exists()
    assert (tmp_path / "configs.json").exists()
    assert (tmp_path / "io.json").exists()

    with open(tmp_path / "results.csv", "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["id"] == "0001"
    assert rows[0]["component_class"] == "ClassA"

    assert (
        json.loads((tmp_path / "configs.json").read_text(encoding="utf-8"))["0001"]
        == config
    )
    assert json.loads((tmp_path / "io.json").read_text(encoding="utf-8"))["0001"] == {
        "inputs": inputs,
        "outputs": outputs,
    }


def test_write_run_config_start(tmp_path: Path) -> None:
    """write_run_config writes config.json with completed=False and timestamps."""
    run_dir = create_run_directory(tmp_path, datetime(2026, 8, 2, 14, 35, 0))
    config = BenchmarkConfig(results_dir=tmp_path)
    start_time = datetime(2026, 8, 2, 14, 35, 0)

    path = write_run_config(
        run_dir,
        command="components",
        start_time=start_time,
        config=config,
        extra={"categories": ["chunking"]},
    )

    assert path == run_dir.config_path == tmp_path / "20260802_143500" / "config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "20260802_143500"
    assert payload["command"] == "components"
    assert payload["completed"] is False
    assert payload["end_time"] is None
    assert payload["start_time"] == start_time.isoformat()
    assert "python_version" in payload["environment"]
    assert "platform" in payload["environment"]
    assert payload["config"]["iterations"] == config.iterations
    assert payload["config"]["has_openai"] is False
    assert payload["extra"] == {"categories": ["chunking"]}


def test_update_run_config_end(tmp_path: Path) -> None:
    """update_run_config marks the run completed with end_time and summary."""
    run_dir = create_run_directory(tmp_path, datetime(2026, 8, 2, 14, 35, 0))
    config = BenchmarkConfig(results_dir=tmp_path)
    write_run_config(
        run_dir,
        command="components",
        start_time=datetime(2026, 8, 2, 14, 35, 0),
        config=config,
    )

    end_time = datetime(2026, 8, 2, 14, 36, 0)
    path = update_run_config(
        run_dir, end_time=end_time, completed=True, summary={"total": 1}
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["completed"] is True
    assert payload["end_time"] == end_time.isoformat()
    assert payload["summary"] == {"total": 1}
    assert payload["start_time"] == "2026-08-02T14:35:00"


def test_update_run_config_missing_config_is_noop(tmp_path: Path) -> None:
    """update_run_config returns the path unchanged when config.json is absent."""
    run_dir = create_run_directory(tmp_path, datetime(2026, 8, 2, 14, 35, 0))

    path = update_run_config(run_dir, end_time=datetime.now(), completed=True)

    assert path == run_dir.config_path
    assert not path.exists()


def test_load_last_run_statuses_recursive(tmp_path: Path) -> None:
    """load_last_run_statuses scans run subfolders recursively."""
    results = tmp_path / "run1" / "components" / "chunking"
    results.mkdir(parents=True)
    (results / "results.csv").write_text(
        _COMPONENT_CSV_HEADER
        + "0001,2026-08-02T14:35:00,chunker,ClassA,ModelX,cfg,passed,1.0,0.5,\n",
        encoding="utf-8",
    )

    statuses = load_last_run_statuses(tmp_path)

    assert statuses[("chunker", "ClassA", "ModelX", "cfg")] == "passed"


def test_load_last_run_statuses_skips_export_csvs(tmp_path: Path) -> None:
    """CSVs without the component status columns are skipped, not fatal."""
    pipelines = tmp_path / "run1" / "pipelines" / "1 - Publication 1 - Medical Fitness"
    pipelines.mkdir(parents=True)
    (pipelines / "results.csv").write_text(
        "id,run_id,pipeline_name,iteration,turn_number,user_message,assistant_response\n"
        "iter0-turn0,iter0,pub1,0,0,hi,hello\n",
        encoding="utf-8",
    )

    statuses = load_last_run_statuses(tmp_path)

    assert statuses == {}


def test_load_last_run_statuses_ignores_skipped_as_latest(tmp_path: Path) -> None:
    """A newer skipped row never overrides a real passed status."""
    results = tmp_path / "run1" / "components" / "chunking"
    results.mkdir(parents=True)
    (results / "results.csv").write_text(
        _COMPONENT_CSV_HEADER
        + "0001,2026-08-02T14:35:00,chunker,ClassA,ModelX,cfg,passed,1.0,0.5,\n"
        + "0002,2026-08-02T14:36:00,chunker,ClassA,ModelX,cfg,skipped,0.0,0.0,\n",
        encoding="utf-8",
    )

    statuses = load_last_run_statuses(tmp_path)

    assert statuses[("chunker", "ClassA", "ModelX", "cfg")] == "passed"


def test_load_last_run_statuses_handles_bom_and_bad_rows(tmp_path: Path) -> None:
    """BOM-prefixed headers and malformed rows are tolerated per row."""
    results = tmp_path / "run1" / "components" / "chunking"
    results.mkdir(parents=True)
    (results / "results.csv").write_text(
        _COMPONENT_CSV_HEADER
        + "0001,2026-08-02T14:35:00,chunker,ClassA,ModelX,cfg,passed,1.0,0.5,\n"
        + "0002,2026-08-02T14:36:00,chunker,ClassB,ModelY\n"
        + "0003,2026-08-02T14:37:00,chunker,ClassC,ModelZ,cfg,weird-status,1.0,0.5,\n",
        encoding="utf-8-sig",
    )

    statuses = load_last_run_statuses(tmp_path)

    assert statuses == {("chunker", "ClassA", "ModelX", "cfg"): "passed"}


def test_atomic_write_json_retries_a_transient_replace_lock(
    tmp_path: Path, monkeypatch
) -> None:
    """A briefly locked destination must not abort the whole benchmark run."""
    from RAG_benchmark.app import store

    target = tmp_path / "configs.json"
    real_replace = Path.replace
    attempts = {"count": 0}

    def flaky_replace(self, destination):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError("file is open in another process")
        return real_replace(self, destination)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    store.atomic_write_json(target, {"0001": {"a": 1}})

    assert attempts["count"] == 3
    assert json.loads(target.read_text(encoding="utf-8")) == {"0001": {"a": 1}}
    assert not (tmp_path / "configs.json.tmp").exists()


def test_atomic_write_json_does_not_retry_a_real_error(
    tmp_path: Path, monkeypatch
) -> None:
    """Errors that will not go away are raised on the first attempt."""
    from RAG_benchmark.app import store

    target = tmp_path / "configs.json"
    attempts = {"count": 0}

    def missing_tmp(self, destination):
        attempts["count"] += 1
        raise FileNotFoundError("temporary file vanished")

    monkeypatch.setattr(Path, "replace", missing_tmp)

    with pytest.raises(FileNotFoundError):
        store.atomic_write_json(target, {})

    assert attempts["count"] == 1
