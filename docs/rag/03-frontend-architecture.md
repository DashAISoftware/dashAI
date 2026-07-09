# Frontend Architecture

## Routes

| Path                              | Component              | Purpose                           |
|-----------------------------------|------------------------|-----------------------------------|
| `/app/generative`                 | `SessionRouter`        | Routes to RAG or non-RAG view     |
| `/app/generative/sessions/:id`    | `RAGSessionPage`       | RAG session detail + chat         |

## Main RAG Page Flow

All files under `pages/generative/rag-session/`:

1. **`RAGSessionSetup.jsx`** — Session creation form with accordion sections:
   - Document selection, chunking config, retriever config (3-preset card
     system), prompt template selection, generator (LLM) config.

2. **`RAGSessionPage.jsx`** — 3-panel orchestrator:
   - Left: session list + document manager
   - Center: setup form / summary view / chat view
   - Right: info bar (educational) / params panel

3. **`GenerativeChat`** — Active chat view (shared with non-RAG sessions).

### Per-Stage Config Sections

Each pipeline stage has a section component in `sections/`:
- `ChunkingSection.jsx`
- `RetrieverSection.jsx`
- `GeneratorSection.jsx`
- `PromptSection.jsx`

### Advanced Configuration Modals

In `advanced/`:
- `CompositeRetrieverBuilder.jsx`
- `ChunkingConfigurationStep.jsx`
- `RetrieverConfigurationStep.jsx`

### Supporting Components

In `components/generative/RAG/`:
- `RAGInfoBar.jsx` — Educational right panel content
- `RAGSessionSummary.jsx` — Session overview
- `RAGParamsPanel.jsx` — Parameter editing

## Key Features

- **Retriever Presets** — 3-card system: Keyword (BM25), Semantic (Dense),
  Hybrid (Sequential BM25 + Dense).
- **Context Window Validation** — Validates that
  `chunk_size * top_k + prompt_tokens <= context_window`.
- **Multi-Language Prompts** — Templates in en/es/pt, selected via dropdown.
- **Translation Keys** — All RAG translations use the `generative:rag.*`
  namespace.

## API Layer

All RAG API calls use standard DashAI endpoints:

| Endpoint                          | Purpose           |
|-----------------------------------|-------------------|
| `/api/v1/generative-session/`     | Session CRUD      |
| `/api/v1/generative-process/`     | Process CRUD      |
| `/api/v1/job/`                    | Job dispatch      |
| `/api/v1/document/`               | Document management |
| `/api/v1/prompt/`                 | Prompt management |
