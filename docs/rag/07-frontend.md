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
- `ChunkingSection`: 4 presets (Small/Paragraph/Page/Large) using `PresetCard` + `AdvancedConfigCard` when custom config applied
- `RetrieverSection`: Paradigm selector using `PresetCard` + Top-K + `AdvancedConfigCard` when custom params applied
- `PromptSection` / `GeneratorSection`: Wrappers around `PromptBody` / `GeneratorBody`
- `DocumentSelector` + `SimplifiedDocumentTable`: MRT-based document picker with upload below table
- `PresetCard`: Unified component for all toggle/card styling — single source of truth for py, px, border, selected-state (amberDim/amberBorder). Used by ChunkingSection presets, RetrieverSection paradigms, and `AdvancedConfigCard`.
- `AdvancedConfigCard`: Clickable card (always `selected` state). Shows "Advanced Configuration Applied" + model name. Clicking re-opens the respective advanced modal with current values pre-filled.

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

9. **Generic FormSchema adoption** (May 2026): RAG-specific form components (`RAGFormSchema`, `RAGFormSchemaRenderFields`, `RAGFormSchemaFieldWithParent`) were deleted. ConfigurationStep components now use the generic `FormSchema` + `FormSchemaContainer`. The generic `FormSchemaFieldWithParent` was fixed to render its sub-modal Dialog (previously clicking the gear icon did nothing). This eliminates ~250 lines of duplicated code and ensures nested model parameter forms work consistently across all modules.

10. **AddModelDialog aesthetic**: Advanced configuration modals follow the same Dialog shell as the models module: `minHeight: "500px"`, `bgcolor: "background.paper"` on all Dialog sections, `variant="outlined"` Cancel button, `variant="subtitle2"` content headings, `gap: 3` content spacing.

11. **PresetCard unification**: `PresetCard` is the single source of truth for all toggle/card styling in RAG sections. Uses same py/px/border/selected-state colors (amberDim/amberBorder/primary.main) as the Top-K selector. Eliminates style drift between toggle buttons and standalone indicator cards. Selected state is managed via the `selected` prop with manual click handlers; MUI `ToggleButtonGroup` is no longer used for preset/paradigm selection to ensure uniform gap spacing with the `AdvancedConfigCard`.
