# Frontend Architecture

## Routes

| Path                              | Component              | Purpose                           |
|-----------------------------------|------------------------|-----------------------------------|
| `/app/generative`                 | `SessionRouter`        | Routes to RAG or non-RAG view     |
| `/app/generative/sessions/:id`    | `RAGSessionPage`       | RAG session detail + chat         |

## Main RAG Page Flow

All files under `pages/generative/RAGSession/`:

1. **`RAGSessionSetup.jsx`** — Session creation form with accordion sections:
   - Document selection, chunking config, retriever config (3-preset card
     system), prompt template selection, generator (LLM) config.
   - Uses `RAGCard`, `SectionCard`, and `RAGSectionColumn` layout components.

2. **`RAGSessionPage.jsx`** — 3-panel orchestrator (uses `ThreePanelLayout`):
   - Left: session list + `RAGDocumentsPanel` (document manager)
   - Center: `RAGSessionSetup` form / `RAGSessionSummary` view / `GenerativeChat` view
   - Right: `RAGInfoBar` (educational) / `RAGParamsPanel` (parameter editing)

3. **`GenerativeChat`** (`components/generative/GenerativeChat.jsx`) — Active chat
   view shared with non-RAG sessions.

### Per-Stage Config Sections

Each pipeline stage has a section component in `sections/`:
- `ChunkingSection.jsx`
- `RetrieverSection.jsx`
- `GeneratorSection.jsx`
- `PromptSection.jsx`

Each section renders inside a `SectionCard` layout wrapper using `RAGSectionColumn`.

### Page-Level Shared Components

In `pages/generative/RAGSession/components/`:
- `RAGCard.jsx` — Accordion-based card with expand/collapse and step indicators
- `SectionCard.jsx` — Flexbox layout wrapper for section content
- `RAGSectionColumn.jsx` — Vertical column layout for stacked sections
- `PresetCard.jsx` — Clickable preset selection card (Keyword/Semantic/Hybrid)
- `GeneratorBody.jsx` — Generator configuration content
- `AdvancedConfigCard.jsx` — Card with navigate-to-advanced-modal button
- `sectionUtils.jsx` — Utility functions (`getDescription`, `renderTemplateWithHighlights`)

### Advanced Configuration Modals

In `advanced/` (9 files):
- `CompositeRetrieverBuilder.jsx` — Visual builder for composite retriever trees
- `RetrieverConfigurationStep.jsx` — Step within composite builder
- `RetrieverAdvancedModal.jsx` — Advanced retriever settings dialog
- `RetrieverNodeConfig.jsx` — Configuration panel for individual retriever nodes
- `ChunkingConfigurationStep.jsx` — Step-level chunking config
- `ChunkingAdvancedModal.jsx` — Advanced chunking settings dialog
- `GeneratorConfigurationStep.jsx` — Step-level generator config
- `GeneratorAdvancedModal.jsx` — Advanced generator settings dialog
- `NewPromptModal.jsx` — Custom prompt creation dialog

### Supporting Components

In `components/generative/RAG/`:
- **Session & summary:** `RAGSessionSummary.jsx`, `RAGBreadcrumbs.jsx`
- **Info & params:** `RAGInfoBar.jsx`, `RAGParamsPanel.jsx`
- **Documents:** `DocumentSelector.jsx`, `DocumentList.jsx`, `DocumentListItem.jsx`,
  `DocumentPreviewModal.jsx`, `DocumentsBar.jsx`, `DocumentTable.jsx`,
  `RAGDocumentsPanel.jsx`
- **Generator:** `GeneratorParamsCard.jsx`
- **Prompts:** `PromptParamsCard.jsx`, `PromptSelectionTable.jsx`,
  `PromptViewModal.jsx`, `PlaceholdersList.jsx`
- **Utilities:** `HighlightedTextarea.jsx`

A `setup/` directory exists with empty `sections/`, `components/`, and `advanced/`
subdirectories, reserved for a future setup-component refactor.

## Key Features

- **Retriever Presets** — 3-card system: Keyword (BM25), Semantic (Dense),
  Hybrid (Sequential BM25 + Dense).
- **Document Selection UI** — Full document table with search, selection,
  preview modal, and multi-select capabilities.
- **Context Window Validation** — Validates that
  `chunk_size * top_k + prompt_tokens <= context_window`.
- **Multi-Language Prompts** — Templates in en/es/pt, selected via dropdown.
- **Template Highlighting** — `renderTemplateWithHighlights()` renders
  `{placeholders}` with colored backgrounds for visual clarity.
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
