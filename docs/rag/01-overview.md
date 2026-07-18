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

| Layer        | Path                                               |
|-------------|----------------------------------------------------|
| Services     | `DashAI/back/services/RAG/`                       |
| Pipeline     | `DashAI/back/models/RAG/RAG_pipeline.py`          |
| Factory      | `DashAI/back/models/RAG/RAG_models_factory.py`     |
| Sub-factories| `DashAI/back/models/RAG/llm_factory.py`, `prompts/prompt_factory.py`, `chunking_models/chunking_model_factory.py`, `retrievers/retriever_factory.py` |
| Constants    | `DashAI/back/models/RAG/RAG_constants.py`          |
| Utilities    | `DashAI/back/models/RAG/utils.py`                  |
| Exceptions   | `DashAI/back/models/RAG/exceptions/`               |
| Retrievers   | `DashAI/back/models/RAG/retrievers/` (subdirs: `dense/`, `sparse/`, `composite/`) |
| Chunking     | `DashAI/back/models/RAG/chunking_models/`         |
| Prompts      | `DashAI/back/models/RAG/prompts/` (subdirs: `generation/`, `augmentation/`) |
| Documents    | `DashAI/back/models/RAG/documents/`               |
| Embeddings   | `DashAI/back/models/RAG/embeddings/` (subdirs: `dense/`, `sparse/`) |
| Jobs         | `DashAI/back/job/RAG_job.py`                     |
| Task         | `DashAI/back/tasks/RAG_task.py`                  |
| Core         | `DashAI/back/core/component_validation.py`        |
| Frontend     | `DashAI/front/src/pages/generative/RAGSession/`   |
| Frontend components | `DashAI/front/src/components/generative/RAG/` |

## Quick Architecture

```
Browser / PyWebView
  → React (port 3000)
    → POST /api/v1/generative-session/   (create session)
      → Validate payload, components, documents, prompt
    → POST /api/v1/generative-process/   (create process)
    → POST /api/v1/job/                  (enqueue job)
      → Huey Job Queue
        → RAGJob.run()
          → RAGSetupService.build_pipeline()
            → DocumentService → ChunkingService → RetrieverSetupService → LLMService
            → RAGPipeline.generate()
          → RAGTask.process_output() (serialize)
        → Frontend polls GET /api/v1/jobs/{id}
```

## Component Types

- **Chunking models** — Character, Token, Recursive character (all implement
  `BaseChunkingModel`)
- **Retrievers** — `RetrieverModel` base; Sparse (TF-IDF, BM25), Dense (via
  `DenseEmbedding` subclasses), Composite (Sequential, Parallel, MMR Reranker)
- **Prompts** — Generation prompts (Default, Custom, QA) in en/es/pt +
  augmentation prompts (Default, Custom) for future query expansion
- **LLMs** — Any `TextToTextGenerationTaskModel` registered in the component
  registry (OpenAI-compatible APIs, HuggingFace models)
- **Embeddings** — `DenseEmbedding` subclasses: BERT, DistilBERT, E5, Gemma,
  HuggingFace, Instructor, LaBSE, OpenAI, RoBERTa, SentenceTransformer,
  FastText
