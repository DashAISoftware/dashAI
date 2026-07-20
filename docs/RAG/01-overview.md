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