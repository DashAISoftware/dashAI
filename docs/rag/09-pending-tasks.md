# 09 — Pending Tasks

Consolidated from `pendientes_rag.md` and current codebase analysis.

## Completed (reference)

### Critical Bugs Fixed
- Cleanup ordering: retriever rows deleted BEFORE chunking models (was silent skip)
- Hardcoded class names: `TFIDFRetriever.__name__` → `instance.__class__.__name__`
- Sparse retriever folder creation: UUID generated before first commit (crash window eliminated)
- `RAGGenerationModel` cleanup: added to `_cleanup_orphaned_rag_resources`

### Refactoring (May 2026)
- Composite retriever pattern (Leaf/Composite/Sequential/Parallel)
- `score_chunks()` on TF-IDF/BM25/Dense for cascade re-ranking
- Strict error handling (ExtraKwargsMissingError, MissingParameterError, etc.)
- MultilingualString + `# type: ignore` on all schemas
- `Persistence` extraction (SparsePersistence, DensePersistence)
- `RetrieverRepository` for all DB queries
- `LLMFactory`, `PipelineRepository`, `DocumentLoader` for pipeline simplification
- `RAGPipeline` simplified to pure orchestration
- `extra_args_enum.py` reduced from 12 to 3 constants
- 4 Alembic migrations (composite, uniqueness, FK inversion, chunk_set)

### Frontend Cleanup (May 2026)
- **Generic `FormSchemaFieldWithParent` fixed**: Added missing sub-modal Dialog (previously clicking the gear icon on nested model fields did nothing). The component had `openSubModal` state and `handleSubModelSave` handler but the `<Dialog>` JSX was never rendered. Now works for all modules.
- **RAG-specific form components deleted**: `RAGFormSchema.jsx`, `RAGFormSchemaRenderFields.jsx`, `RAGFormSchemaFieldWithParent.jsx` — all 3 were nearly identical copies of generic components. ConfigurationStep components (`ChunkingConfigurationStep`, `RetrieverConfigurationStep`, `GeneratorConfigurationStep`) now use `FormSchema` + `FormSchemaContainer` directly.
- **`PresetCard` unified component**: Single source of truth for toggle/card styling. Used by ChunkingSection presets, RetrieverSection paradigms, and `AdvancedConfigCard`. Same selected-state colors (amberDim/amberBorder) as Top-K selector.
- **`AdvancedConfigCard` component**: Clickable card showing "Advanced Configuration Applied" + model name. Replaces the old text caption and Custom toggle button. Clicking re-opens the advanced modal with current values pre-filled.
- **`AddModelDialog` aesthetic applied**: Advanced configuration modals now match the platform's Dialog shell style (`minHeight: "500px"`, `bgcolor: "background.paper"`, `variant="outlined"` Cancel button, `variant="subtitle2"` headings, `gap: 3` spacing).
- **No `ToggleButtonGroup`**: Preset/paradigm selection uses manual `Box flex gap: 1` with `PresetCard` components. Ensures uniform spacing between toggle items and `AdvancedConfigCard`.

---

## Pending Items

### 0. Remove dead `persistence.py`
`DashAI/back/models/RAG/persistence.py` is unused dead code (zero imports anywhere). Its `DensePersistence` has fields `(embedding_model_id, env_path, existing)` but the actual used class at `retrievers/persistence.py` has `(matrix_dirs, embedding_model_id)`. Remove the root-level file.

### 1. Split RetrieverModelsFactory
The factory is 333 lines and handles three concerns:
- Lookup orchestration (repo calls)
- Persistence planning (build SparsePersistence/DensePersistence)
- Composite recursion (child construction)

**Target**: split into `RetrieverConstructor` (unit retriever instantiation) + `CompositeOrchestrator` (child recursion).

### 2. Update `generative_session.py` Cleanup
The cleanup logic in `DashAI/back/api/api_v1/endpoints/generative_session.py` currently references old schema columns. Must be updated to use `RetrieverRepository` and the bridge/chunk_set FK chain.

### 3. Chunk Cleanup on Document Removal
`chunking_models_factory.py:update_db_models()` creates new chunks but never deletes old ones. If documents are removed from a session, chunks for removed documents remain orphaned.
- Impact: disk space waste, no correctness issue.
- Fix: add deletion of chunks whose `document_id` is no longer in the session's document list, scoped to the chunk_set.

### 4. Prompt Cleanup Heuristic
Prompts are cleaned up only if their name contains `" - session {id}"`. Custom-named prompts are never cleaned.
- Fix: add FK from prompt to GenerativeSession, or use `RAGPipeline.prompt_id` to trace owner.

### 5. `_load_composite_from_db` Filtering
Currently queries by `class_name` only. In a multi-pipeline setup with same composite class, wrong row could be returned.
- Mitigation: in practice, each session has its own pipeline.
- Fix: join through `RAGRetriever.pipeline_id` to filter by pipeline_id.

### 6. Frontend Form for Composites
Composite retrievers have `children` removed from pydantic schema. The frontend needs a UI for selecting composite children without the `children` field in auto-generated forms.
- Approach: metadata-only approach — factory passes composite config via separate endpoint or special schema field.

### 7. `RAGDocumentPipelineSessionLink` Migration
This is the only RAG model still using legacy `Column()` syntax. All others use `Mapped[]` + `mapped_column()`.
- Impact: purely cosmetic, but breaks consistency.

### 8. ParserFactory
When document parsers become first-class components (currently hardcoded in BaseDocument subclasses), a `ParserFactory` pattern analogous to `LLMFactory` should be created.

### 9. Test Coverage
- Backend RAG tests are minimal. Need tests for:
  - Composite retriever recursion (sequential + parallel strategies)
  - `score_chunks` on all retriever types
  - Chunk_set deterministic reuse
  - Persistence dataclass lifecycle (None → set → save)
  - Exception triggering paths (missing kwargs, composite validation, cascade child errors)
  - Cleanup ordering (retriever before chunking)

### 10. Database Migration Verification
The 4 migrations were generated but need end-to-end verification:
- Fresh DB creation runs all 4 without errors
- Existing DB with legacy schema migrates without data loss
- Unique constraints don't block normal operation (reuse paths work)

## Deprecated Code to Remove

| Location | Item | Replacement | Status |
|----------|------|-------------|--------|
| `RAGPipeline._ensure_pipeline_db_row` | No-op stub | `PipelineRepository.ensure_row` | REMOVED |
| `RAGPipeline._update_pipeline_db_row` | No-op stub | `PipelineRepository.update_row` | REMOVED |
| `RAGPipeline.load_documents_from_db` | Already removed earlier | `DocumentLoader.load` | DONE |
| `RAGPipeline.validate_params` | Instance method validation | `RAGPipelineConfig.from_kwargs` | REMOVED (folded into config) |
| `RAGPipeline.print()` | Debug statement | (removed) | REMOVED |
| `simplified-RAG/components/RAGFormSchema.jsx` | RAG-specific FormSchema clone | Generic `FormSchema` | REMOVED (May 2026) |
| `simplified-RAG/components/RAGFormSchemaRenderFields.jsx` | RAG-specific render fields clone | Generic `FormSchemaRenderFields` | REMOVED (May 2026) |
| `simplified-RAG/components/RAGFormSchemaFieldWithParent.jsx` | RAG-specific parent field (sub-modal) | Generic `FormSchemaFieldWithParent` (fixed) | REMOVED (May 2026) |
| Old cleanup in `generative_session.py` | References old columns | Update to use RetrieverRepository | PENDING |

## Next Steps (Priority Order)

1. Test full flow end-to-end (fresh session → chunk_set → chunking → retriever → persistence → retrieval)
2. Update `generative_session.py` cleanup to use new schema
3. Split `RetrieverModelsFactory` into `RetrieverConstructor` + `CompositeOrchestrator`
4. Add retriever tests (composite recursion, scoring, exception paths)
5. Implement frontend composite children UI
6. Add chunk cleanup on document removal
