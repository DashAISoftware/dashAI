# Frontend Architecture

## Routes

| Path | Component | Purpose |
|------|-----------|---------|
| `/app/generative` | `SessionRouter` | Routes to RAG or non-RAG view |
| `/app/generative/sessions/:id` | `SessionRouter` | Detects RAGTask, renders `RAGSessionPage` |
| `/app/generative/rag/documents` | `RAGDocumentsPage` | Standalone document manager |
| `/app/generative/rag/prompts` | `RAGPromptsPage` | Standalone prompt manager |

## Main RAG Page Flow

All files under `pages/generative/rag-session/`:

1. **`RAGSessionPage.jsx`** — 3-panel orchestrator:
   - Left panel: session list + document manager
   - Center panel: setup form / summary view / chat view
   - Right panel: info bar (educational) / params panel

2. **`RAGSessionSetup.jsx`** — Session creation form with accordion sections:
   - Document selection
   - Chunking configuration
   - Retriever configuration (3-preset card system)
   - Prompt template selection
   - Generator (LLM) configuration

3. **`RAGSessionSummary.jsx`** — Post-creation overview with a button to start chatting.

4. **`GenerativeChat`** — Active chat view (shared with non-RAG generative sessions).

### Per-Stage Config Sections

Each pipeline stage has a dedicated section component in `sections/`:
- `ChunkingSection.jsx`
- `RetrieverSection.jsx`
- `GeneratorSection.jsx`
- `PromptSection.jsx`

### Advanced Configuration Modals

For advanced users, modals in `advanced/` provide full control:
- `CompositeRetrieverBuilder.jsx`
- `ChunkingConfigurationStep.jsx`
- `RetrieverConfigurationStep.jsx`

### Supporting Components

In `components/generative/RAG/`:
- `RAGInfoBar.jsx` — Educational right panel content
- `RAGSessionSummary.jsx` — Session overview
- `RAGParamsPanel.jsx` — Parameter editing
- `RAGDocumentsPanel.jsx` — Document management panel

## Key Frontend Decisions

### Retriever Presets
The retriever section uses a 3-preset card system: Keyword (BM25), Semantic (DenseEmbedding), Hybrid (Sequential BM25 + Dense).
Advanced detection compares the current model config (minus `top_k`) against the 3 presets to determine which preset to highlight.

### Context Window Validation
The generator section validates that `chunk_size * top_k + prompt_tokens <= context_window` to prevent overflows.

### Multi-Language Prompts
Prompt templates support en/es/pt. They are registered in the component registry and selected via a dropdown.

### Translation Keys
All RAG frontend translations use the `generative:rag.*` namespace.

## API Layer

All RAG API calls are in `api/rag.ts`:
- Session CRUD: `/api/v1/generative-session/`
- Process CRUD: `/api/v1/generative-process/`
- Job dispatch: `/api/v1/job/`
- Document management: `/api/v1/document/`
- Prompt management: `/api/v1/prompt/`
