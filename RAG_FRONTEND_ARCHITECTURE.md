# RAG Frontend Architecture — AI Agent Reference

> Auto-generated index of all files involved in the RAG simplified view,
> session summary, generative chat, and side panels.
> Last updated: 2026-05-14

---

## 1. Routes (registered in `App.jsx`)

| Route | Component | Purpose |
|-------|-----------|---------|
| `/app/generative/rag` | `SimplifiedRAGPage` | Main RAG page (3-panel: setup/summary/chat) |
| `/app/generative/rag/documents` | `RAGDocumentsPage` | Detailed document management view |
| `/app/generative/rag/prompts` | `RAGPromptsPage` | Detailed prompt management view |

The legacy RAGHomePage, RAGSessionsPage, and /sessions route have been removed. Selecting "RAG Task" from `/app/generative` navigates directly to `/app/generative/rag`.

---

## 2. Simplified RAG View — Complete File Tree

```
pages/generative/simplified-RAG/
├── SimplifiedRAGPage.jsx            ← Entry point: 3-panel orchestrator
├── SimplifiedSessionSetup.jsx       ← Session creation form (replaces CenterBox with custom wrapper)
│
├── sections/                        ← Creation form sections
│   ├── ChunkingSection.jsx          ← Chunking presets (Small/Paragraph/Page/Large)
│   ├── RetrieverSection.jsx         ← Retriever paradigm selector + Top-K
│   ├── PromptSection.jsx            ← Thin wrapper: description always visible, no info toggle
│   └── GeneratorSection.jsx         ← Thin wrapper: description always visible, no info toggle
│
├── components/                      ← Shared subcomponents
│   ├── SectionCard.jsx              ← Consistent spacing Box (replaced Card wrapper)
│   ├── PromptBody.jsx               ← Core prompt logic + autocomplete + template + new prompt btn
│   ├── GeneratorBody.jsx            ← Core generator logic + autocomplete + context stats + advanced btn
│   ├── sectionUtils.jsx             ← getDescription(), renderTemplateWithHighlights()
│   ├── ragFormDefaults.js           ← buildDefaultValuesFromSchemaProperties, getInitialModelParameters (relocated)
│   ├── RAGFormSchema.jsx            ← RAG-specific form schema renderer
│   ├── RAGFormSchemaRenderFields.jsx← Field renderer for RAGFormSchema
│   └── RAGFormSchemaFieldWithParent.jsx ← Nested model param field
│
└── advanced/                        ← Advanced config modals + configuration step components (relocated)
    ├── ChunkingAdvancedModal.jsx    ← Dialog wrapping ChunkingConfigurationStep
    ├── ChunkingConfigurationStep.jsx← Full chunking model config form (RELOCATED from NewSessionModal)
    ├── RetrieverAdvancedModal.jsx   ← Dialog wrapping RetrieverConfigurationStep
    ├── RetrieverConfigurationStep.jsx← Full retriever config form (RELOCATED from NewSessionModal)
    ├── GeneratorAdvancedModal.jsx   ← Dialog wrapping GeneratorConfigurationStep
    ├── GeneratorConfigurationStep.jsx← Full generator config form (RELOCATED from NewSessionModal)
    ├── PromptAdvancedModal.jsx      ← Standalone prompt advanced dialog
    └── NewPromptModal.jsx           ← Create-new-prompt dialog (shared with PromptSelectionTable)
```

---

## 3. RAG Side Panels & Shared Components

```
components/generative/RAG/
├── SimplifiedRAGInfoBar.jsx         ← Right panel: educational info (no session selected)
├── RAGParamsPanel.jsx               ← Right panel: edit prompt + LLM (session selected)
│   ├── PromptParamsCard.jsx         ← Collapsible card: info toggle, selector always visible
│   └── GeneratorParamsCard.jsx      ← Collapsible card: info toggle, selector always visible
│
├── RAGSessionSummary.jsx            ← Center panel: session overview before chat
│   └── RAGBreadcrumbs.jsx           ← Breadcrumb navigation
│
├── RAGDocumentsPanel.jsx            ← Left panel: session documents
│   └── DocumentsBar.jsx             ← Document list sidebar
│       ├── DocumentList.jsx         ← Scrollable list
│       │   └── DocumentListItem.jsx ← Single document row
│       └── DocumentPreviewModal.jsx ← PDF/TXT preview (normalizeUrl with API_ORIGIN)
│
├── DocumentSelector.jsx             ← Document picker in creation form (upload btn below table)
│   └── SimplifiedDocumentTable.jsx  ← MRT table with checkbox selection
│
├── DocumentTable.jsx                ← Full document table (RAGDocumentsPage)
├── PromptSelectionTable.jsx         ← Full prompt table (RAGPromptsPage, uses simplified NewPromptModal)
├── PlaceholdersList.jsx             ← {chunks}/{input} help text
├── DocumentPreviewModal.jsx         ← Shared preview modal (normalizeUrl)
└── RAGBreadcrumbs.jsx               ← Navigation (used by summary, chat, detail pages)
```

---

## 4. Dependency Graph

```
SimplifiedRAGPage
├── [Left]   SessionBar
├── [Left]   RAGDocumentsPanel → DocumentsBar → DocumentList → DocumentListItem
│                                                   └→ DocumentPreviewModal
├── [Center] SimplifiedSessionSetup  (no session selected)
│   ├── DocumentSelector → SimplifiedDocumentTable → DocumentPreviewModal
│   ├── ChunkingSection → ChunkingAdvancedModal → ChunkingConfigurationStep
│   ├── RetrieverSection → RetrieverAdvancedModal → RetrieverConfigurationStep
│   ├── PromptSection → SectionCard → PromptBody → PromptAdvancedModal
│   │                                               └→ NewPromptModal → PlaceholdersList
│   └── GeneratorSection → SectionCard → GeneratorBody → GeneratorAdvancedModal
│                                                       └→ GeneratorConfigurationStep
├── [Center] RAGSessionSummary / GenerativeChat
│   └── RAGBreadcrumbs
├── [Right]  SimplifiedRAGInfoBar   (no session selected)
└── [Right]  RAGParamsPanel         (session selected)
    ├── PromptParamsCard → PromptBody
    └── GeneratorParamsCard → GeneratorBody
```

---

## 5. Shared Utilities

| File | Exports | Used by |
|------|---------|---------|
| `api/rag.ts` | All RAG API calls | Most components |
| `simplified-RAG/components/ragFormDefaults.js` | `buildDefaultValuesFromSchemaProperties`, `getInitialModelParameters` | ChunkingSection, RetrieverSection, GeneratorBody, GeneratorConfigurationStep, ChunkingConfigurationStep, RetrieverConfigurationStep |
| `utils/schema.js` | `getModelFromSubform`, `getParamsFromSubform`, `formattedSubform` | ChunkingSection, RAGFormSchemaRenderFields, RAGFormSchemaFieldWithParent |
| `utils/urlUtils.js` | `normalizeUrl` | DocumentPreviewModal, SimplifiedDocumentTable, DocumentList, DocumentTable |
| `contexts/schema.js` | `FormSchemaProvider`, `useFormSchemaStore` | RAGFormSchemaFieldWithParent, advanced modals |

---

## 6. Component Responsibilities

| Component | Context | Role |
|-----------|---------|------|
| `SimplifiedRAGPage` | Page | 3-panel orchestrator. Session selection state, toggles setup/summary/chat |
| `SimplifiedSessionSetup` | Creation | Multi-accordion form. Own wrapper (not CenterBox) with sticky Cancel/Save buttons |
| `RAGSessionSummary` | Summary | Session config overview, "Open Chat" transitions to GenerativeChat |
| `GenerativeChat` | Chat | Generic chat UI. RAG: renders `RAGBreadcrumbs` + `SourcesDisplay` |
| `RAGParamsPanel` | Right panel | Edit prompt + LLM. Dirty-tracking + save. Cards collapsed by default |
| `SimplifiedRAGInfoBar` | Right panel | Static educational content about RAG (shown during creation) |
| `RAGDocumentsPanel` | Left panel | Session documents via `DocumentsBar` |

---

## 7. Key Architectural Decisions

1. **Single RAG view**: `/app/generative/rag` → `SimplifiedRAGPage`. Legacy `RAGHomePage`, `RAGSessionsPage`, `NewSessionModal` wizard all deleted. Selecting "RAG Task" at `/app/generative` navigates here directly.

2. **Dual card system**: Creation uses `PromptSection`/`GeneratorSection` (description always visible, no info toggle, no inner collapse — Accordion handles it). Params bar uses `PromptParamsCard`/`GeneratorParamsCard` (info toggle, collapsible with selector always visible). Both share `PromptBody`/`GeneratorBody`.

3. **`showDetails` prop**: Controls whether body components render full details or just the selector. Params cards collapse without unmounting the selector, showing the selected model name in the dropdown even when collapsed.

4. **Advanced modals are self-contained**: `ChunkingConfigurationStep`, `RetrieverConfigurationStep`, `GeneratorConfigurationStep` were relocated from `NewSessionModal/` into `simplified-RAG/advanced/`. No more legacy directory dependencies.

5. **Sequential naming**: `SimplifiedSessionSetup` fetches sessions directly via `getSessions()` on mount (bypassing prop/context chain). Uses `useState` + `useEffect` instead of `useMemo` + `useRef` to avoid React 18 StrictMode double-fire bugs.

6. **Document preview URL normalization**: `utils/urlUtils.js` exports `normalizeUrl()` which extracts the API origin from `REACT_APP_API_URL` and prepends it to relative URLs. Backend `download_document` uses RFC 5987 `filename*=UTF-8''` encoding for Unicode filenames.

7. **Sticky action buttons**: `SimplifiedSessionSetup` uses a flex layout with `height: 100%` and `flex: 1` scrollable middle area. Cancel/Save buttons are `flexShrink: 0` at the bottom, always visible without needing scroll.

8. **Consistent spacing**: `SectionCard` + `AccordionDetails` with `px: 4` ensures uniform horizontal padding. No Card wrapper nesting issues (previous Prompt/Generator had extra padding).

9. **Chunk size display**: Presets show `[n chars] caracteres ≈ [n tokens] tokens` via i18n interpolation. ToggleButton text uses sentence case with `textTransform: "none"` to override MUI theme uppercase.

10. **DocumentSelector**: Upload button moved below table. `minHeight` removed from table wrapper for natural sizing.
