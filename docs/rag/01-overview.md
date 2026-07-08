# RAG Module Overview

## What is RAG in DashAI

Retrieval-Augmented Generation (RAG) lets users upload documents and chat with them. The pipeline retrieves relevant document chunks and feeds them to an LLM as context for grounded answers.

## Pipeline Stages

1. **Document Loading** — Load documents from the repository into memory.
2. **Chunking** — Split documents into chunks using a configurable chunking model.
3. **Retrieval** — Find the most relevant chunks for the user's query via sparse, dense, or composite retrievers.
4. **Generation** — Inject retrieved chunks into a prompt template and generate a response via an LLM.

## Code Location

| Layer | Path |
|-------|------|
| Backend | `DashAI/back/models/RAG/` |
| Frontend | `DashAI/front/src/pages/generative/rag-session/` |
| Jobs | `DashAI/back/job/rag_job.py` |
| Task | `DashAI/back/tasks/RAG_task.py` |

## Quick Architecture

```
FastAPI endpoint
  → Huey job (RAGJob)
    → RAGPipeline
      → DocumentLoader → ChunkingModel → Retriever → LLM
    → Response serialized via RAGTask
  → Frontend polls job status
```

## Component Types

- **Chunking models** — `RecursiveTokenChunker`, `SentenceChunker`, etc.
- **Retrievers** — Sparse (TFIDF, BM25), Dense (SentenceTransformer, BERT), Composite (Sequential, Parallel, MMR)
- **Prompts** — Multi-language prompt templates (en/es/pt) registered as components
- **LLMs** — Wrappers for OpenAI-compatible APIs, HuggingFace models, etc.
