# RAG Module Overview

## What is RAG in DashAI

Retrieval-Augmented Generation (RAG) lets users upload documents and have
conversations with them. The pipeline retrieves relevant document chunks for
each user query and feeds them to an LLM as context, producing grounded
answers that cite the source material.

## Pipeline Stages

```
User query
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                  1. Document Loading                      │
│   Load Document rows from the DB and hydrate in-memory   │
│   BaseDocument objects (txt, pdf, md, csv, rst, tex).   │
└──────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                  2. Chunking                              │
│   Split each document into smaller pieces using one of:  │
│     • CharacterChunkModel    — fixed-size char windows   │
│     • TokenChunkModel        — token-aware splitting     │
│     • RecursiveCharacterChunk — separator-priority split │
│   Chunks are persisted to the DB and cached by SHA-256   │
│   signature for reuse across sessions.                   │
└──────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                  3. Retrieval                             │
│   Find the top-k most relevant chunks for the query via: │
│     • Sparse retrievers    — TF-IDF, BM25                │
│     • Dense retrievers     — embedding-based similarity  │
│     • Composite retrievers — Sequential, Parallel, MMR   │
│   (Composite pattern: leaf + composite nodes)            │
└──────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                  4. Generation                            │
│   Inject chunks into a prompt template and generate a    │
│   response via an LLM. Supports multi-language prompts   │
│   (en/es/pt) and custom templates.                      │
└──────────────────────────────────────────────────────────┘
     │
     ▼
   Response + cited chunks (returned as JSON)
```

## Code Location

| Layer     | Path                                          |
|-----------|-----------------------------------------------|
| Pipeline  | `DashAI/back/models/RAG/RAG_pipeline.py`      |
| Factories | `DashAI/back/models/RAG/rag_models_factory.py` |
| Retrievers| `DashAI/back/models/RAG/retrievers/`          |
| Chunking  | `DashAI/back/models/RAG/chunking_models/`     |
| Prompts   | `DashAI/back/models/RAG/prompts/`             |
| Documents | `DashAI/back/models/RAG/documents/`           |
| Embeddings| `DashAI/back/models/RAG/embeddings/`          |
| Jobs      | `DashAI/back/job/rag_job.py`                 |
| Task      | `DashAI/back/tasks/RAG_task.py`              |
| Frontend  | `DashAI/front/src/pages/generative/rag-session/` |

## Quick Architecture

```
Browser / PyWebView
  → React (port 3000)
    → POST /api/v1/generative-session/   (create session)
    → POST /api/v1/generative-process/   (create process)
    → POST /api/v1/job/                  (enqueue job)
      → Huey Job Queue
        → GenerativeJob.run()
          → RAGJob.run() (if RAGTask detected)
            → RAGPipeline.generate()
              → DocumentLoader → ChunkingModel → Retriever → LLM
            → RAGTask.process_output() (serialize)
          → Frontend polls GET /api/v1/jobs/{id}
```

## Component Types

- **Chunking models** — Character, Token, Recursive character (all implement
  `BaseChunkingModel`)
- **Retrievers** — Sparse (TF-IDF, BM25), Dense (via `DenseEmbedding`
  subclasses), Composite (Sequential, Parallel, MMR Reranker)
- **Prompts** — Generation prompts (Default, Custom, QnA) in en/es/pt +
  augmentation prompts (Default, Custom) for future query expansion
- **LLMs** — Any `TextToTextGenerationTaskModel` registered in the component
  registry (OpenAI-compatible APIs, HuggingFace models)
