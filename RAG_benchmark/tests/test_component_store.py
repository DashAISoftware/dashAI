"""Unit tests for the shared DashAI component-store helpers.

Covers ``ensure_component_store`` (register the default config service that
the download mixin reads at call time), ``ensure_component_downloaded``
(download-or-fail gating before a model is instantiated), the recursive
component-reference walker used by the pipeline pre-flight, and the pipeline
runner's behaviour when that pre-flight fails. No model downloads or DashAI
app are required.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from RAG_benchmark.app.benchmark_utils import (
    ensure_component_downloaded,
    ensure_component_store,
)
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.pipelines.base import _iter_component_refs
from RAG_benchmark.app.pipelines.configs import PIPELINE_REGISTRY
from RAG_benchmark.app.pipelines.runner import (
    _failed_pipeline_result,
    run_pipeline_benchmarks,
)


class _NotDownloadable:
    """Class without ``REQUIRES_DOWNLOAD`` whose API must never be called."""

    @classmethod
    def is_downloaded(cls) -> bool:
        raise AssertionError("is_downloaded must not be called")

    @classmethod
    def download(cls, report=None) -> None:
        raise AssertionError("download must not be called")


class _MissingDownloadApi:
    """Class that claims to require a download but lacks the API."""

    REQUIRES_DOWNLOAD = True


def _make_downloadable(*, downloaded: bool) -> type:
    """Build a fresh fake downloadable class with the given initial state."""

    class FakeModel:
        REQUIRES_DOWNLOAD = True
        DOWNLOAD_SIZE_BYTES = 123
        download_calls = 0

        @classmethod
        def is_downloaded(cls) -> bool:
            return downloaded

        @classmethod
        def download(cls, report=None) -> None:
            cls.download_calls += 1

    return FakeModel


def test_ensure_component_downloaded_noop_without_requires_download() -> None:
    """A class without ``REQUIRES_DOWNLOAD`` is left untouched."""
    ensure_component_downloaded(_NotDownloadable)  # must not raise


def test_ensure_component_downloaded_noop_without_download_api() -> None:
    """A download-flagged class lacking the API is skipped, not crashed."""
    ensure_component_downloaded(_MissingDownloadApi)  # must not raise


def test_ensure_component_downloaded_skips_present_artifacts() -> None:
    """When ``is_downloaded`` is True, ``download`` is never called."""
    fake = _make_downloadable(downloaded=True)

    ensure_component_downloaded(fake)

    assert fake.download_calls == 0


def test_ensure_component_downloaded_downloads_once_when_missing(capsys) -> None:
    """A missing component is downloaded exactly once, with its class name."""
    fake = _make_downloadable(downloaded=False)

    ensure_component_downloaded(fake)

    assert fake.download_calls == 1
    assert "FakeModel" in capsys.readouterr().out


def test_ensure_component_downloaded_raises_without_download_flag() -> None:
    """``download=False`` fails fast naming the class and ``--no-download``."""
    fake = _make_downloadable(downloaded=False)

    try:
        ensure_component_downloaded(fake, download=False)
    except RuntimeError as error:
        message = str(error)
        assert "FakeModel" in message
        assert "--no-download" in message
        assert "component store" in message
    else:  # pragma: no cover - the call above must raise
        raise AssertionError("Expected RuntimeError for a missing component")
    assert fake.download_calls == 0


def test_ensure_component_store_is_idempotent(monkeypatch) -> None:
    """The first call registers ``config``; a second call keeps it as-is."""
    fake_di: dict = {}
    build_calls = []

    def fake_build(**kwargs):
        build_calls.append(kwargs)
        return {"COMPONENT_PATH": "/fake/components"}

    monkeypatch.setattr("kink.di", fake_di)
    monkeypatch.setattr(
        "DashAI.back.dependencies.config_builder.build_config_dict",
        fake_build,
    )

    ensure_component_store()
    first_config = fake_di["config"]
    ensure_component_store()

    assert fake_di["config"] is first_config
    assert first_config == {"COMPONENT_PATH": "/fake/components"}
    assert len(build_calls) == 1


def test_iter_component_refs_finds_nested_refs() -> None:
    """Refs nested in dict-in-list-in-dict are yielded in traversal order."""
    params = {
        "outer": {
            "component": "A",
            "params": {
                "children": [
                    {"component": "B", "params": {}},
                    {"nested": {"component": "C"}},
                ]
            },
        }
    }

    names = [ref["component"] for ref in _iter_component_refs(params)]

    assert names == ["A", "B", "C"]


def test_failed_pipeline_result_defaults() -> None:
    """The helper builds a non-skipped failure with zeroed timings."""
    result = _failed_pipeline_result("Pub X", "boom")

    assert result.pipeline_name == "Pub X"
    assert result.success is False
    assert result.skipped is False
    assert result.error_message == "boom"
    assert result.turns == []
    assert result.document_ids == []
    assert result.total_time_ms == 0.0
    assert result.total_chunks_retrieved == 0


def test_pipeline_preflight_failure_skips_iterations(tmp_path: Path) -> None:
    """A failed pre-flight records a failed result and never runs the pipeline."""
    config = BenchmarkConfig(results_dir=tmp_path)

    with patch(
        "RAG_benchmark.app.pipelines.runner.PipelineBenchmarkRunner"
    ) as mock_runner_cls:
        instance = mock_runner_cls.return_value
        instance.ensure_models_available.side_effect = RuntimeError("missing qwen")
        result = run_pipeline_benchmarks(config, pipelines=["pub1"])

    instance.setup.assert_called_once()
    instance.ensure_models_available.assert_called_once()
    assert instance.ensure_models_available.call_args.kwargs == {"download": True}
    instance.run_pipeline.assert_not_called()
    instance.teardown.assert_called_once()

    assert len(result.pipeline_results) == 1
    failed = result.pipeline_results[0]
    assert failed.pipeline_name == PIPELINE_REGISTRY["pub1"]["name"]
    assert failed.success is False
    assert failed.error_message == "missing qwen"
    assert result.summary["failed"] == 1
    assert result.summary["total_pipelines_run"] == 1
