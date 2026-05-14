# RAG Frontend Architecture — AI Agent Reference

> Auto-generated index of all files involved in the RAG simplified view,
> session summary, generative chat, and side panels.
> Last updated: 2026-05-13

---

## 1. Entry Points (routes registered in `App.jsx`)

| Route | Component | File |
|-------|-----------|------|
| `/app/generative/rag` | `SimplifiedRAGPage` | `pages/generative/simplified-RAG/SimplifiedRAGPage.jsx` |
| `/app/generative/RAG` | `RAGHomePage` ⚠️ LEGACY | `pages/generative/RAG/RAGHomePage.jsx` |
| `/app/generative/rag/sessions` | `RAGSessionsPage` ⚠️ LEGACY | `pages/generative/RAG/RAGSessionsPage.jsx` |
| `/app/generative/rag/documents` | `RAGDocumentsPage` ⚠️ LEGACY | `pages/generative/RAG/RAGDocumentsPage.jsx` |
| `/app/generative/rag/prompts` | `RAGPromptsPage` ⚠️ LEGACY | `pages/generative/RAG/RAGPromptsPage.jsx` |

> ⚠️ = Legacy view, to be removed. Simplified view (`SimplifiedRAGPage`) will become the only RAG view.

---

## 2. Simplified RAG View — Complete File Tree

```
pages/generative/simplified-RAG/
├── SimplifiedRAGPage.jsx          ← Entry point (3-panel layout)
├── SimplifiedSessionSetup.jsx     ← Session creation form (center panel, no session selected)
│
├── sections/                      ← Creation form sections (used by SimplifiedSessionSetup)
│   ├── ChunkingSection.jsx        ← Chunking strategy selector + presets
│   ├── RetrieverSection.jsx       ← Retriever paradigm selector + Top-K
│   ├── PromptSection.jsx          ← Prompt selector (wraps PromptBody)
│   ├── GeneratorSection.jsx       ← LLM selector (wraps GeneratorBody)
│   └── index.js                   ★ UNUSED barrel file
│
├── components/                    ← Shared subcomponents
│   ├── SectionCard.jsx            ← Consistent spacing wrapper (used by Prompt/Generator sections)
│   ├── PromptBody.jsx             ← Core prompt logic (autocomplete, template, new prompt btn)
│   ├── GeneratorBody.jsx          ← Core generator logic (autocomplete, context stats, advanced btn)
│   ├── sectionUtils.jsx           ← getDescription(), renderTemplateWithHighlights()
│   ├── RAGFormSchema.jsx          ← RAG-specific form schema renderer (used by legacy wizard steps)
│   ├── RAGFormSchemaRenderFields.jsx ← Field renderer for RAGFormSchema
│   └── RAGFormSchemaFieldWithParent.jsx ← Nested model param field
│
└── advanced/                      ← Advanced config modals
    ├── ChunkingAdvancedModal.jsx  ← Delegates to ChunkingConfigurationStep (legacy)
    ├── RetrieverAdvancedModal.jsx ← Delegates to RetrieverConfigurationStep (legacy)
    ├── GeneratorAdvancedModal.jsx ← Delegates to GeneratorConfigurationStep (legacy)
    ├── PromptAdvancedModal.jsx    ← Standalone (no legacy dependency)
    ├── NewPromptModal.jsx         ← Create-new-prompt dialog
    └── index.js                   ★ UNUSED barrel file
```

---

## 3. RAG Side Panels & Shared Components

```
components/generative/RAG/
├── SimplifiedRAGInfoBar.jsx       ← Right panel: educational info (when no session selected)
├── RAGParamsPanel.jsx             ← Right panel: edit prompt + LLM (when session selected)
│   ├── PromptParamsCard.jsx       ← Collapsible prompt card with info toggle
│   └── GeneratorParamsCard.jsx    ← Collapsible LLM card with info toggle
│
├── RAGSessionSummary.jsx          ← Center panel: session overview before entering chat
│   └── RAGBreadcrumbs.jsx         ← Navigation breadcrumbs
│
├── RAGDocumentsPanel.jsx          ← Left panel: session documents (when session selected)
│   └── DocumentsBar.jsx           ← Document list sidebar
│       ├── DocumentList.jsx       ← Scrollable document list
│       │   └── DocumentListItem.jsx ← Single document row
│       └── DocumentPreviewModal.jsx ← PDF/TXT preview modal
│
├── DocumentSelector.jsx           ← Document picker (used in creation form)
│   └── SimplifiedDocumentTable.jsx ← Checkbox-based document table (MaterialReactTable)
│
├── PlaceholdersList.jsx           ← Renders {chunks}/{input} help text (used by NewPromptModal)
│
└── RAGBreadcrumbs.jsx             ← Navigation breadcrumbs (used by multiple pages)

GenerativeChat.jsx (parent dir) renders:
  └── RAGBreadcrumbs.jsx           ← Shown when task is RAG
  └── SourcesDisplay.jsx           ← Document reference chips on RAG messages
```

---

## 4. Dependency Graph — Simplified View

```
SimplifiedRAGPage
├── [Left]   SessionBar
├── [Left]   RAGDocumentsPanel → DocumentsBar → DocumentList → DocumentListItem
│                                                      └→ DocumentPreviewModal
├── [Center] SimplifiedSessionSetup  (no session selected)
│   ├── ChunkingSection → ChunkingAdvancedModal → ChunkingConfigurationStep (legacy)
│   ├── RetrieverSection → RetrieverAdvancedModal → RetrieverConfigurationStep (legacy)
│   ├── PromptSection → SectionCard → PromptBody → PromptAdvancedModal
│   │                                           └→ NewPromptModal → PlaceholdersList
│   ├── GeneratorSection → SectionCard → GeneratorBody → GeneratorAdvancedModal
│   │                                                  └→ GeneratorConfigurationStep (legacy)
│   └── DocumentSelector → SimplifiedDocumentTable → DocumentPreviewModal
│
├── [Center] RAGSessionSummary      (session selected, chat not active)
│   └── RAGBreadcrumbs
│
├── [Center] GenerativeChat         (chat active)
│   ├── RAGBreadcrumbs
│   └── SourcesDisplay
│
├── [Right]  SimplifiedRAGInfoBar   (no session selected)
└── [Right]  RAGParamsPanel         (session selected)
    ├── PromptParamsCard → PromptBody
    └── GeneratorParamsCard → GeneratorBody
```

---

## 5. Shared Utilities (cross-directory)

| File | Exports | Used by |
|------|---------|---------|
| `api/rag.ts` | `getRAGPrompts`, `getGeneratorComponents`, `getChunkingComponents`, `getRetrievalParadigm`, `getRetrieverComponents`, `loadDocuments`, `createRAGSession`, `updateGenerativeSessionParams`, etc. | Most components |
| `RAG/NewSessionModal/ragFormDefaults.js` | `buildDefaultValuesFromSchemaProperties`, `getInitialModelParameters` | ChunkingSection, RetrieverSection, GeneratorBody, ChunkingConfigurationStep, GeneratorConfigurationStep, RetrieverConfigurationStep |
| `utils/schema.js` | `getModelFromSubform`, `getParamsFromSubform`, `formattedSubform`, etc. | ChunkingSection, RAGFormSchemaRenderFields, RAGFormSchemaFieldWithParent |
| `contexts/schema.js` | `FormSchemaProvider`, `useFormSchemaStore` | RAGFormSchemaFieldWithParent, advanced modals |

---

## 6. Dead Code — Safe to Delete

| File | Reason |
|------|--------|
| `simplified-RAG/sections/index.js` | Barrel file — never imported |
| `simplified-RAG/advanced/index.js` | Barrel file — never imported |
| `components/generative/RAG/DocumentSelectionTable.jsx` | Never imported anywhere |
| `components/generative/RAG/SessionMetadata.jsx` | Never imported anywhere |
| `pages/generative/RAG/AlgorithmConfigurationStep.jsx` | Never imported |
| `pages/generative/RAG/ModelConfigurationStep.jsx` | Never imported |
| `pages/generative/RAG/RetrieverConfigurationStep copy.jsx` | Backup copy |

---

## 7. Legacy View Files (to remove when migrating to simplified-only)

These files are ONLY used by the legacy `RAGHomePage` and its sub-pages. They do NOT serve the simplified view:

| File | Notes |
|------|-------|
| `pages/generative/RAG/RAGHomePage.jsx` | Legacy main page |
| `pages/generative/RAG/RAGSessionsPage.jsx` | Legacy sessions list |
| `pages/generative/RAG/RAGSessionsTable.jsx` | Legacy sessions MRT table |
| `pages/generative/RAG/RAGDocumentsPage.jsx` | Legacy documents page |
| `pages/generative/RAG/RAGPromptsPage.jsx` | Legacy prompts page |
| `pages/generative/RAG/NewSessionModal/NewSessionModal.jsx` | Multi-step wizard orchestrator |
| `pages/generative/RAG/NewSessionModal/DocumentSelectionStep.jsx` | Wizard step 1 |
| `pages/generative/RAG/NewSessionModal/PromptConfigurationStep.jsx` | Wizard step 4 |
| `components/generative/RAG/DocumentTable.jsx` | Full-featured document table |
| `components/generative/RAG/PromptSelectionTable.jsx` | Full prompt management table |
| `components/generative/RAG/ComponentSelector.jsx` | Generic component picker |
| `components/generative/RAG/NewPromptModal.jsx` | Legacy new-prompt (duplicate of simplified version) |

### Legacy files that the simplified view STILL depends on:

| File | Used by |
|------|---------|
| `pages/generative/RAG/NewSessionModal/ChunkingConfigurationStep.jsx` | `ChunkingAdvancedModal` |
| `pages/generative/RAG/NewSessionModal/RetrieverConfigurationStep.jsx` | `RetrieverAdvancedModal` |
| `pages/generative/RAG/NewSessionModal/GeneratorConfigurationStep.jsx` | `GeneratorAdvancedModal` |
| `pages/generative/RAG/NewSessionModal/ragFormDefaults.js` | `ChunkingSection`, `RetrieverSection`, `GeneratorBody` |

> These 4 files need to be relocated out of `NewSessionModal/` when the legacy wizard is deleted.

---

## 8. Component Responsibilities (Quick Reference)

| Component | Context | What it does |
|-----------|---------|-------------|
| `SimplifiedRAGPage` | Page | 3-panel orchestrator. Manages session selection state, toggles between setup/summary/chat |
| `SimplifiedSessionSetup` | Creation | Multi-accordion form. Collects name, docs, chunking, retriever, prompt, generator. Calls `createRAGSession` |
| `RAGSessionSummary` | Summary | Shows session config overview. "Open Chat" button transitions to `GenerativeChat` |
| `GenerativeChat` | Chat | Generic chat UI. RAG-specific: renders `RAGBreadcrumbs` + `SourcesDisplay` for document references |
| `RAGParamsPanel` | Right panel | Edit prompt + LLM of an existing session. Dirty-tracking + save button |
| `SimplifiedRAGInfoBar` | Right panel | Static educational content about RAG concepts (shown during creation) |
| `RAGDocumentsPanel` | Left panel | Shows session documents via `DocumentsBar` |

---

## 9. Key Architectural Decisions

1. **3-panel layout**: Left (sessions/docs), Center (setup/summary/chat), Right (info/params). State managed in `SimplifiedRAGPage` via `useGenerative` context.

2. **Dual card system**: Creation uses `PromptSection`/`GeneratorSection` (desc always visible, no info toggle). Params bar uses `PromptParamsCard`/`GeneratorParamsCard` (info toggle, collapsible). Both share `PromptBody`/`GeneratorBody`.

3. **`showDetails` prop**: Controls whether body components render full details (template, context stats, buttons) or just the selector. Used by params cards to collapse without unmounting the selector.

4. **Legacy dependency**: Advanced modals delegate to legacy `*ConfigurationStep` components. These will need relocation when legacy is removed.

5. **Consistent spacing**: `SectionCard` wrapper + `AccordionDetails` with `px: 4` ensures uniform horizontal padding across all creation sections.
