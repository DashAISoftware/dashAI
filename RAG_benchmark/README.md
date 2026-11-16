# RAG benchmark

Local benchmark harness for the DashAI RAG stack. It exercises the registered
chunkers, text embeddings, retrievers, query-transformation stages, prompts and
GGUF language models, plus the thesis pipeline configurations.

This directory is a working copy that is **not tracked as a whole**: runtime
data, downloaded papers, results and credentials stay local. Only the source
under `app/` and `tests/` is meant to be versioned.

## Running

From the repository root:

```bash
python -m RAG_benchmark.app.cli components --iter 1
python -m RAG_benchmark.app.cli pipelines --iter 1
```

Useful options:

- `--device auto|CPU|GPU|CUDA` — device for llama.cpp checkpoints.
- `--category` (repeatable) — component categories to run.
- `--pipeline` (repeatable) — pipeline keys (`pub1` … `pub5c`).
- `--no-download` — fail instead of downloading a missing GGUF checkpoint.
- `--skip-passes` — reuse the statuses of the previous run.

## Qwen 3

`Qwen3_8B` is part of the benchmark matrix and is the default function-calling
model for the query-transformation and agentic-retrieval rows:

- `app/components/llm.py` benchmarks `qwen3-8b-concise` and
  `qwen3-8b-creative`.
- `app/components/transformation.py` benchmarks the rewriter, expander and
  decomposer with Qwen2.5 1.5B, Qwen2.5 7B and Qwen3 8B.
- `app/components/retrieval.py` uses `Qwen3_8B` as the agentic retrievers'
  function-calling model.
- `app/pipelines/configs.py` uses `Qwen3_8B` in `pub5a`, `pub5b` and `pub5c`.

Qwen3 is loaded with `enable_thinking=False` (see
`DashAI/back/models/hugging_face/qwen_model.py`), so the model emits the
structured function call instead of a reasoning trace.

## Local-only files

The following are intentionally excluded from version control:

- `.env` (API credentials).
- `data/` (SQLite database, chunk sets, embeddings, sparse retrievers).
- `papers/` (benchmark PDFs).
- `results/`, `results_backup/`, `discarded_results/`.
- `__pycache__/`.

## Known local limitations

- `papers/` must contain at least one PDF before the component and pipeline
  benchmarks can parse the corpus.
- Some publication configurations still reference `OpenAIEmbedding`, which is
  not registered in the current DashAI build. Those rows fail until the
  embedding component is available or the config is rebased to a local
  embedding model.
- The harness was reconstructed from local session history after only
  `__pycache__` remained; validate a full run before relying on old result
  files.
