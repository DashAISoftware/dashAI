# 07 — Frontend Architecture

> See also: `RAG_FRONTEND_ARCHITECTURE.md` (158 lines) and Section 2 of `RAG_TECHNICAL_GUIDE.md` (288 lines) for full discussions. This document condenses the key information.

## Routes

| Route | Component | Purpose |
|-------|-----------|---------|
| `/app/generative/rag` | `SimplifiedRAGPage` | Main 3-panel RAG interface |
| `/app/generative/rag/documents` | `RAGDocumentsPage` | Document management |
| `/app/generative/rag/prompts` | `RAGPromptsPage` | Prompt management |

Legacy routes removed: `/app/generative/rag/sessions`, `/app/generative/RAG`, `/app/generative/simplified-rag`.

## 3-Panel Layout

```
SimplifiedRAGPage
├── LeftPanel
│   ├── SessionBar (no session)      ← session list
│   └── RAGDocumentsPanel (session)  ← DocumentsBar + DocumentPreviewModal
├── CenterPanel
│   ├── SimplifiedSessionSetup (no session)  ← creation form
│   ├── RAGSessionSummary (session, pre-chat) ← config overview
│   └── GenerativeChat (session, active)     ← chat + References section
└── RightPanel
    ├── SimplifiedRAGInfoBar (no session)  ← educational content
    └── RAGParamsPanel (session)          ← PromptParamsCard + GeneratorParamsCard
```

## Dual Card System

| Aspect | Creation (`PromptSection`/`GeneratorSection`) | Params Bar (`PromptParamsCard`/`GeneratorParamsCard`) |
|--------|----------------------------------------------|------------------------------------------------------|
| Description | Always visible | Info toggle (ℹ️) to show/hide |
| Collapse | Outer Accordion controls it | Internal `ExpandMoreIcon` |
| Default | Expanded | Collapsed (selector always visible) |
| Shared core | `PromptBody` / `GeneratorBody` with `showDetails` prop | Same core |

## Key Frontend Components

### Creation Flow
- `SimplifiedSessionSetup`: Multi-accordion form with sticky Cancel/Save buttons
- `ChunkingSection`: 4 presets (Small/Paragraph/Page/Large) with dynamic char→token descriptions
- `RetrieverSection`: Paradigm selector + Top-K
- `PromptSection` / `GeneratorSection`: Wrappers around `PromptBody` / `GeneratorBody`
- `DocumentSelector` + `SimplifiedDocumentTable`: MRT-based document picker with upload below table

### Session View
- `RAGSessionSummary`: Config overview, "Open Chat" button → transitions to chat
- `RAGParamsPanel`: Edit prompt + LLM. Cards collapsed by default. Dirty-tracking + save.
- `GenerativeChat`: Generic chat UI. For RAG: renders `RAGBreadcrumbs` + `SourcesDisplay`.
- `DocumentPreviewModal`: PDF in `<iframe>`, TXT in `<pre>`. Uses `normalizeUrl()` with `API_ORIGIN`.

### Shared Utilities
- `api/rag.ts`: All RAG API calls
- `components/ragFormDefaults.js`: `buildDefaultValuesFromSchemaProperties`, `getInitialModelParameters`
- `utils/schema.js`: `getModelFromSubform`, `getParamsFromSubform`, `formattedSubform`
- `utils/urlUtils.js`: `normalizeUrl()` — prepends API origin to relative paths

## Key Design Decisions

1. **Single RAG view**: Legacy `RAGHomePage`, `RAGSessionsPage`, `NewSessionModal` wizard all deleted
2. **`showDetails` prop**: Controls body component detail rendering without unmounting selector
3. **Sequential naming**: Direct `getSessions()` fetch on mount avoids React 18 StrictMode ref-timing bug
4. **Document preview**: `normalizeUrl()` solves relative URL issue; backend uses RFC 5987 encoding
5. **Sticky buttons**: Flex layout keeps Cancel/Save fixed at bottom
6. **Chunking presets**: Dynamic `[chars] caracteres ≈ [tokens] tokens` descriptions with i18n
7. **Document upload**: Button moved below table; `minHeight` removed for natural sizing
8. **Reactive validation**: `chunk_size * top_k + prompt_tokens ≤ LLM context window` checked before creation
