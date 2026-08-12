# Document Processing Plan — Per-Document Extractor Selection

## Motivation

Currently every document is processed with a **hardcoded extractor**: `PDFDocument` defaults
to `textract` (the `PyPDF2` parser branch exists but is never reached), and every other file
type is read as plain text. The `parser` parameter in `PDFDocument.__init__` is dead code —
`DocumentService.load()` never passes it.

This plan introduces **per-document extractor selection** so users can choose which parser
processes each document. The extractor is designed as a **ComponentRegistry component**
(following the same pattern as chunking models, retrievers, and prompts), enabling future
extensions such as OCR, LLM-based post-processing, CSV-to-text converters, and full
extraction pipelines.

## Design Decisions & Tradeoffs

### 1. Extractor as a ComponentRegistry component

**Decision**: register extractors in the `ComponentRegistry`, not as a simple string column.

**Rationale**:

- Consistent with every other ML component in DashAI (chunking, retrieval, embeddings,
  prompts, LLMs).
- Frontend auto-generates the selector form from the component schema — no hardcoded
  dropdown lists.
- `get_child_components(parent, recursive=False)` uses direct base classes (`__bases__`)
  to discover children (`component_registry.py:392–425`). Each concrete extractor
  subclassing `BaseExtractor` directly is exposed via
  `getChildComponents("BaseExtractor", false)`.
- Extensible to OCR / CSVs / LLM post-processing by registering new subclasses.
- Schema params (`lang`, `dpi`, etc.) come for free with the `ConfigObject` + `BaseSchema`
  pattern.
- The chunk-set signature can instantly include `{doc_id → {component, params}}`,
  making cache invalidation deterministic and per-document.

**Tradeoff**: slightly more boilerplate than a string column (base class, schema,
registration). The investment pays off on the very next extractor addition.

### 2. Storage: dedicated JSON column on `document`

**Decision**: new `document.extractor JSON` column storing `{component, params}` (same shape
as `chunking_model` in session parameters), `nullable`.

**Rejected alternative — `optional_metadata`**: `DocumentService.upload()` overwrites
`optional_metadata` wholesale on hash-dedup (`document_service.py:128–133`), which would
clobber the extractor choice. A dedicated column avoids this entirely and is strongly typed.

**Rejected alternative — `VARCHAR` string column**: a plain name (`"pymupdf"`, `"textract"`)
cannot carry parameters (e.g. OCR `lang`, `dpi`). JSON avoids a future migration when
parameterized extractors arrive.

### 3. Invalidation strategy: explicit deletion + signature as backstop

When a document's extractor changes:

- **Explicit deletion**: delete the document's chunks, embedding matrices (DB + `.npy`
  directories), sparse retriever storage, and the chunk set(s) containing the document.
  Retrievers referencing those chunk sets are also removed (bridges, detail rows,
  composite children, disk artifacts).
- **Signature backstop**: `_build_chunk_set_signature` (`chunking_service.py:39–50`)
  incorporates `{doc_id → extractor_ref}`, so even if deletion misses something, the
  next pipeline run creates a fresh chunk set.
- **Recomputation**: lazy — next time a RAG pipeline runs for an affected session, chunking
  - retrieval recompute automatically. No new background job is required for
    re-extraction.

**Deletion scope**: the _entire_ chunk set is invalidated (not just the changed document's
chunks), because all retrievers built on that chunk set become stale. This affects every
RAG session that shares the chunk set — the user is warned and must confirm before the
change is committed.

**Existing gap fixed**: `DocumentService.delete()` already cascades `Chunk` and
`RAGEmbeddingMatrix` rows, but leaves orphaned chunk sets, retriever bridges, sparse
retriever folders, and embedding `.npy` files. The same invalidation logic can be called
on document deletion, closing that gap.

### 4. On-demand text preview

A `POST /api/v1/document/{id}/extract` endpoint extracts text with a given extractor
(optional; defaults to the stored one) **without persisting**. This powers the
"Procesar documento y mostrar contenido" button in the documents view. Extraction
can be slow for large files or OCR — the frontend shows a loading spinner.

### 5. Confirmation flow on extractor change

When the user saves an extractor change:

1. Backend checks if the document is linked to any RAG pipeline.
2. If linked and no `force` flag → `409 Conflict` with a list of affected session IDs and
   names.
3. Frontend shows a confirmation dialog: "Este cambio afectará a N pipeline(s) RAG.
   Se eliminarán los chunks y retrievers y se recomputarán en la próxima ejecución.
   ¿Continuar?"
4. On confirm → re-call with `force=true` → backend persists the new extractor, deletes
   affected artifacts, returns the updated document.

## Target Architecture

```
Extractors package:
DashAI/back/models/RAG/extractors/
├── __init__.py              — public API
├── base_extractor.py        — BaseExtractor(ConfigObject), TYPE="Extractor"
├── plain_text_extractor.py  — PlainTextExtractor (txt, md, rst, tex, csv)
├── textract_extractor.py    — TextractExtractor (pdf)
├── pypdf2_extractor.py      — PyPDF2Extractor (pdf)
└── pymupdf_extractor.py     — PyMuPDFExtractor (pdf) — new dependency
```

```
Data model addition:
document table
  + extractor: JSON (nullable)  → {"component": "PyMuPDFExtractor", "params": {}}
```

```
Endpoints:
POST /api/v1/document/{id}/extract   — on-demand text extraction (no persistence)
PUT  /api/v1/document/{id}/extractor — commit extractor choice + invalidate
```

## New Component: `BaseExtractor`

| Attribute              | Value                                                                   |
| ---------------------- | ----------------------------------------------------------------------- |
| File                   | `DashAI/back/models/RAG/extractors/base_extractor.py`                   |
| Parent                 | `ConfigObject`                                                          |
| `TYPE`                 | `"Extractor"`                                                           |
| `SCHEMA`               | `BaseSchema` (empty; subclasses may override)                           |
| `SUPPORTED_FILE_TYPES` | `[]` (abstract — overridden per concrete extractor)                     |
| `get_metadata()`       | returns `{"supported_file_types": ["pdf"], ...}` for frontend filtering |

Methods:

- `extract(file_path: str) -> str` — abstract.

### Concrete extractors

| Class                | File types               | Backend                                         | File                                 |
| -------------------- | ------------------------ | ----------------------------------------------- | ------------------------------------ |
| `TextractExtractor`  | `pdf`                    | `textract.process()` + `_clean_textract_output` | `extractors/textract_extractor.py`   |
| `PyPDF2Extractor`    | `pdf`                    | `PyPDF2.PdfReader`                              | `extractors/pypdf2_extractor.py`     |
| `PyMuPDFExtractor`   | `pdf`                    | `pymupdf` (`fitz`)                              | `extractors/pymupdf_extractor.py`    |
| `PlainTextExtractor` | `txt, md, rst, tex, csv` | `open(file_path).read()`                        | `extractors/plain_text_extractor.py` |

Every extractor is **stateless** — instantiated once per document hydration.

## Data Model

### Migration

New Alembic revision adding one column to `document`:

```python
def upgrade():
    with op.batch_alter_table("document", schema=None) as batch_op:
        batch_op.add_column(sa.Column("extractor", sa.JSON(), nullable=True))
```

No data migration — `None` ⇒ default extractor resolved by file type at hydration time.

### Column

| Column      | Type   | Nullable | Purpose                                                           |
| ----------- | ------ | -------- | ----------------------------------------------------------------- |
| `extractor` | `JSON` | `true`   | `{component: str, params: dict}`. `None` ⇒ use file-type default. |

### DocumentResponse schema update

`DocumentResponse` (`schemas/document.py`) gains:

```python
extractor: Optional[Dict[str, Any]]  # {component, params}
```

## Extractor Resolution

`DocumentService.__init__` now receives `registry: ComponentRegistry`. `load()` resolves
the extractor per document:

1. Read `db_doc.extractor` (JSON component-ref) or `None`.
2. If `None` → resolve the **file-type default** (e.g. `"TextractExtractor"` for PDF,
   `"PlainTextExtractor"` for TXT).
3. Instantiate via `registry[name]["class"](**params)`.

`BaseDocument.__init__` receives `extractor: BaseExtractor` and `get_text()` delegates to
`self.extractor.extract(self.file_path)`. The existing `PDFDocument` / `TxtDocument`
subclasses become thin (they only set defaults and provide metadata).

### Call sites affected

All callers of `DocumentService(db)` need `registry`:

- `setup_service.py:56`
- `session_validation_service.py:64`
- `endpoints/documents.py` (5 endpoint handlers)
- `tests/back/RAG/conftest.py` and related tests

## Chunk Set Signature Update

`chunking_service.py:_build_chunk_set_signature` adds the per-document extractor mapping:

```python
def _build_chunk_set_signature(self, document_ids, pipeline_config):
    extractors = {}
    for doc_id in sorted(document_ids):
        db_doc = self._db.query(DocumentDBModel).get(doc_id)
        extractors[str(doc_id)] = db_doc.extractor or "default"
    payload = json.dumps(
        {
            "doc_ids": sorted(document_ids),
            "doc_extractors": dict(sorted(extractors.items())),
            "config": dict(sorted(pipeline_config.items())),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()
```

This ensures:

- Same extractor per doc → same signature → chunk set cache hit.
- Different extractor for any doc → different signature → new chunk set.

## Invalidation: `CleanupService.invalidate_document_artifacts(document_id)`

Reuses the existing `_delete_path`, `_cleanup_sparse_retriever`, and dense cleanup patterns
from `CleanupService` (`cleanup_service.py`).

### Steps

1. Query `RAGChunkSetDocument` for the document → list of `chunk_set_id`s.
2. For each chunk set:
   - **Sparse retrievers**: find `RAGSparseRetriever` rows matching `chunk_set_id` →
     delete `storage_folder` on disk → delete detail row → delete bridge (cascade removes
     `RAGRetrieverChunkSet` links).
   - **Dense retrievers**: find `RAGDenseRetriever` rows matching `chunk_set_id` →
     collect `embedding_model_id`s → for each document in the chunk set, delete
     `RAGEmbeddingMatrix` rows + `.npy` directories on disk (`EmbeddingStorageService.
delete_storage`) → delete bridge (cascade removes detail) → optionally delete
     `RAGEmbeddingModel` if now unreferenced.
   - **Composite retrievers**: after deleting child bridges, find `RAGRetrieverChild`
     rows where `child_id` was deleted → delete parent bridges and their `RAGRetrieverChild`
     links.
   - **Chunk set**: delete `RAGChunkSet` (cascade removes `Chunk`, `RAGChunkSetDocument`,
     `RAGEmbeddingMatrix`, and `RAGRetrieverChunkSet` rows).
3. Commit.

## API Contract

### `POST /api/v1/document/{document_id}/extract`

On-demand text extraction. **Does not persist anything.**

Request:

```json
{
  "extractor": { "component": "PyMuPDFExtractor", "params": {} }
}
```

(`extractor` is optional; defaults to the document's stored extractor.)

Response `200`:

```json
{
  "text": "Extracted content here...",
  "extractor": { "component": "PyMuPDFExtractor", "params": {} },
  "char_count": 12345
}
```

Errors: `404` (document not found), `400` (extractor not compatible with file type, or
extraction failure — `RAGDocumentParsingError`), `422` (invalid extractor ref).

### `PUT /api/v1/document/{document_id}/extractor`

Commit an extractor change and optionally invalidate RAG artifacts.

Request:

```json
{
  "extractor": { "component": "PyMuPDFExtractor", "params": {} },
  "force": false
}
```

Response `200` (no pipelines, or `force=true`):

```json
{
  "id": 1,
  "file_name": "report.pdf",
  "file_type": "pdf",
  "extractor": { "component": "PyMuPDFExtractor", "params": {} },
  "...": "..."
}
```

Response `409 Conflict` (has pipelines, `force=false`):

```json
{
  "detail": "Document is linked to 2 RAG pipeline(s). Changing the extractor will delete existing chunks and retrievers. Use force=true to proceed.",
  "affected_sessions": [
    { "id": 10, "name": "My RAG session" },
    { "id": 15, "name": "Project analysis" }
  ]
}
```

Errors: `404` (document not found), `400` (extractor not compatible with file type),
`422` (invalid extractor ref, or extractor not found in registry).

## Frontend Changes

### New component: `DocumentDetailPanel` (right panel of `/documents`)

Currently the right panel of `RAGDocumentsPage` is empty (`RAGDocumentsPage.jsx:165–177`).
It becomes a detail panel:

- **Document info**: name, type, size, created date.
- **Current extractor**: name displayed (e.g. "textract").
- **Extractor selector**: dropdown filtered by `file_type` compatibility (fetched via
  `getChildComponents("BaseExtractor", false)`, metadata includes `supported_file_types`).
- **Content display**: fetched on-demand via `POST /extract` with the current extractor
  (lazy load, spinner).
- **Change flow**:
  1. User selects a different extractor → button **"Procesar documento y mostrar
     contenido"** becomes visible.
  2. Click → `POST /extract` with the new extractor → content renders below (on-demand
     processing).
  3. A save action **"Guardar extractor"** commits: `PUT /extractor` with `force=false`.
     - If `200` → extractor saved, artifact cleanup runs, refresh document list.
     - If `409` → confirmation dialog listing the affected session names → on accept,
       `PUT /extractor` with `force=true` → saved + invalidated.

### `DocumentTable.jsx`

New column **"Extractor"** showing the current extractor's `component` name.
Clicking a row selects the document in the detail panel. The delete action also benefits
from the invalidation cleanup (closing the orphaned-artifacts gap).

### `DocumentSelector.jsx` (setup wizard)

Optionally shows the extractor as an informative read-only column. No changes to the
session-creation flow for this iteration.

### API client (`api/rag.ts`)

```typescript
getExtractorOptions(): Promise<IComponent[]>         // getChildComponents("BaseExtractor", false)
extractDocumentText(docId, extractorRef): Promise<{text, extractor, char_count}>
updateDocumentExtractor(docId, extractorRef, force): Promise<IDocumentResponse>
```

### i18n

New translation keys in `generative.json` (en, es, pt, zh, de) under:

- `rag.documents.extractor` (column header)
- `rag.documents.processAndShowContent` (button label)
- `rag.documents.saveExtractor` (save action)
- `rag.documents.changeExtractorConfirmTitle` / `changeExtractorConfirmBody` (dialog)
- `ragDocumentsPage.detailPanel.*` (right panel labels)

## Registration in `get_initial_components()`

```python
# Extractors
TextractExtractor,
PyPDF2Extractor,
PyMuPDFExtractor,
PlainTextExtractor,
```

They appear in the registry under `TYPE="Extractor"` and the frontend discovers them via
`getChildComponents("BaseExtractor", false)` (direct base-class lookup).

## Dependencies

| Package    | Status                              | Purpose             |
| ---------- | ----------------------------------- | ------------------- |
| `textract` | already in `requirements.txt`       | `TextractExtractor` |
| `pypdf2`   | already in `requirements.txt`       | `PyPDF2Extractor`   |
| `pymupdf`  | **new** — add to `requirements.txt` | `PyMuPDFExtractor`  |

## Testing

### Backend

| Test file                                 | What it covers                                                                                                                                                                                                |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_extractors.py`                      | Each extractor extracts text from a real file; `get_metadata()` exposes `supported_file_types`; incompatible file-type raises error.                                                                          |
| `test_extractor_signature.py`             | Changing a document's extractor produces a different chunk-set signature; same extractor keeps the same signature.                                                                                            |
| `test_document_extractor_api.py`          | `POST /extract` returns text on demand; `PUT /extractor` returns `200` for docs without pipelines; `409` with `affected_sessions` for docs with pipelines; `force=true` succeeds and deletes artifacts.       |
| `test_document_extractor_invalidation.py` | Create chunk set + retriever (dense + sparse + composite), change extractor with `force=true`, verify that chunk rows, chunk sets, retriever bridges, embedding matrices, and disk artifacts are all deleted. |

### Frontend

| Test file                      | What it covers                                                                                                                                                                                              |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DocumentDetailPanel.test.tsx` | Renders document info; dropdown shows compatible extractors filtered by file type; button appears when selection differs; "Procesar y mostrar" calls extract endpoint; confirmation dialog on 409 response. |
| `rag.test.ts` (or inline)      | `getExtractorOptions`, `extractDocumentText`, `updateDocumentExtractor` API functions.                                                                                                                      |

Update existing tests that construct `DocumentService(db)` or `PDFDocument(parser=...)`:

- `tests/back/RAG/conftest.py` — `DocumentService(db, registry)`.
- Any test using `PDFDocument(parser="PyPDF2")` directly — migrate to the extractor.

## Edge Cases & Risks

| Case                                                          | Handling                                                                                                                                                                                                                                                 |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`textract` binary not installed**                           | `textract` requires system-level tools (e.g. `pdftotext`). Extraction fails with `RAGDocumentParsingError`. The frontend shows the error in the preview panel.                                                                                           |
| **Shared chunk set across sessions**                          | Deleting a chunk set invalidates _all_ sessions that share it. The confirmation dialog warns the user with exact session names before proceeding.                                                                                                        |
| **Pre-migration documents (`extractor = NULL`)**              | `DocumentService.load()` resolves the file-type default when `extractor` is `None`. No breakage.                                                                                                                                                         |
| **Large PDFs / OCR**                                          | `POST /extract` is synchronous. Large files may take seconds. The frontend loading spinner handles this. A future iteration can move extraction to a background job.                                                                                     |
| **Composite retrievers with children in affected chunk sets** | The invalidation explicitly finds parent composite bridges via `RAGRetrieverChild.child_id` matching deleted child bridges, then removes them.                                                                                                           |
| **Embedding model records shared across chunk sets**          | `RAGEmbeddingModel` is only cleaned up if no remaining `RAGDenseRetriever` references it. Conservative — no false deletions.                                                                                                                             |
| **Concurrent extractor change + pipeline run**                | The extractor column belongs to the document, not the session. If a pipeline is running while the extractor changes, the running job has already loaded the documents (old content). The next run picks up the new extractor. Acceptable race condition. |

## Out of Scope (Future Iterations)

- **Extraction pipeline** (multi-stage: extract → clean → OCR → LLM post-process). The JSON
  column design (single ref) is the first step; v2 generalizes to a list of component
  refs (`extraction_pipeline: [{component, params}, ...]`).
- **Structured parsers**: `CsvExtractor`, `MarkdownTableExtractor`.
- **Eager recomputation** via background job on extractor change.
- **Cached extracted text** in the database (avoid re-extracting on every preview load).
- **OCR-specific extractors** with language, DPI, and page-range parameters.
- **Extractor validation report** (compare extraction quality across backends).
