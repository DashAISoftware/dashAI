"""Incremental results writer for pipeline benchmarks.

One ``PipelineResultsWriter`` is created per pipeline run folder. It writes
one CSV row per conversation turn and stores the redacted pipeline config
(per iteration) and per-turn inputs/outputs in JSON stores, all incrementally.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from RAG_benchmark.app.models import TurnRecord
from RAG_benchmark.app.store import (
    CONFIGS_JSON_FILENAME,
    IO_JSON_FILENAME,
    RESULTS_CSV_FILENAME,
    JsonStore,
    append_csv_row,
    csv_single_line,
)

#: Column names of the per-turn ``results.csv`` file.
TURN_CSV_COLUMNS = [
    "id",
    "run_id",
    "pipeline_name",
    "iteration",
    "turn_number",
    "user_message",
    "assistant_response",
    "retrieval_time_ms",
    "transformation_time_ms",
    "generation_time_ms",
    "total_turn_time_ms",
    "chunks_retrieved",
    "queries",
    "retrieved_chunks",
    "prompt_length_chars",
    "response_length_chars",
    "error",
]


class PipelineResultsWriter:
    """Writes a pipeline's results incrementally into one run folder.

    Parameters
    ----------
    folder : Path
        Directory for this pipeline's files (created if missing).
    pipeline_name : str
        Human-readable pipeline name, stored on every turn row.
    """

    def __init__(self, folder: Path, pipeline_name: str) -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.pipeline_name = pipeline_name
        self.csv_path = self.folder / RESULTS_CSV_FILENAME
        self.configs = JsonStore(self.folder / CONFIGS_JSON_FILENAME)
        self.io = JsonStore(self.folder / IO_JSON_FILENAME)

    def write_config(self, run_id: str, config: Dict[str, Any]) -> None:
        """Store the redacted pipeline config for one iteration."""
        self.configs.set(run_id, config)

    def append_turn(
        self,
        turn_id: str,
        run_id: str,
        pipeline_name: str,
        iteration: int,
        turn: TurnRecord,
    ) -> None:
        """Record one conversation turn as a CSV row and an io.json entry.

        The JSON store is written before the CSV row so that, on a crash
        between writes, the per-turn inputs/outputs remain recoverable.
        """
        self.io.set(
            turn_id,
            {
                "inputs": {
                    "user_message": turn.user_message,
                    "turn_number": turn.turn_number,
                },
                "outputs": {
                    "assistant_response": turn.assistant_response,
                    "retrieved_chunks": turn.retrieved_chunks,
                    "chunks_retrieved": turn.chunks_retrieved,
                    "queries": list(turn.queries),
                    "retrieval_time_ms": turn.retrieval_time_ms,
                    "transformation_time_ms": turn.transformation_time_ms,
                    "generation_time_ms": turn.generation_time_ms,
                    "total_turn_time_ms": turn.total_turn_time_ms,
                    "prompt_length_chars": turn.prompt_length_chars,
                    "response_length_chars": turn.response_length_chars,
                    "error": turn.error,
                },
            },
        )
        append_csv_row(
            self.csv_path,
            TURN_CSV_COLUMNS,
            {
                "id": turn_id,
                "run_id": run_id,
                "pipeline_name": pipeline_name,
                "iteration": iteration,
                "turn_number": turn.turn_number,
                "user_message": csv_single_line(turn.user_message),
                "assistant_response": csv_single_line(turn.assistant_response),
                "retrieval_time_ms": f"{turn.retrieval_time_ms:.2f}",
                "transformation_time_ms": f"{turn.transformation_time_ms:.2f}",
                "generation_time_ms": f"{turn.generation_time_ms:.2f}",
                "total_turn_time_ms": f"{turn.total_turn_time_ms:.2f}",
                "chunks_retrieved": turn.chunks_retrieved,
                "queries": csv_single_line(
                    json.dumps(list(turn.queries), ensure_ascii=False)
                ),
                "retrieved_chunks": json.dumps(
                    turn.retrieved_chunks, ensure_ascii=False
                ),
                "prompt_length_chars": turn.prompt_length_chars,
                "response_length_chars": turn.response_length_chars,
                "error": csv_single_line(turn.error or ""),
            },
        )
