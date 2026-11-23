# Known Limitations and Operational Notes

## Performance

- **Chunk similarity matrices are held in RAM.** Works for low hundreds of
  documents but will not scale to millions. No out-of-core or approximate
  indexing.

- **Chunk sets are not shared between sessions.** Documents belong to the Data
  module, but `RAGChunkSet.signature` includes the owning session id alongside
  the document ids, so it always differs. Two sessions configured identically
  over the same Data documents each chunk them and fit their own retriever.
  This is the accepted cost of session isolation; the parsed document folder on
  disk is shared, since it belongs to the Data document.

- **No streaming.** The frontend waits for the full LLM response before
  displaying it. Streaming support is not implemented.

- **No FAISS or HNSW indexing.** Dense retrieval performs O(n*dim) brute-force
  similarity search per query. Large document collections will be slow.

- **Cross-encoder retrievers** perform O(n) pair scoring per query over
  candidate chunks from the child retriever. With large candidate sets
  (controlled by the child's own `top_k`), this can be slow on CPU.

- **Generation occupies the single Huey worker.** `RAGJob` holds no database
  session while the LLM runs — it loads and builds in one session and saves the
  output in a second — but the model load and inference are synchronous and
  take the worker's only slot, so other queued jobs wait for the whole turn.

- **The optional query-transformation stage adds an LLM call per turn.** When
  enabled, one model call — and possibly a distinct model instance — runs
  before any retrieval, ahead of the generation call itself.

- **`n` transformed queries mean `n` retriever calls per turn.** Retrieval runs
  once per query and merges the ranked lists round-robin, de-duplicating by
  `(document_id, document_position)`; there is no score fusion. The only
  re-ranking is the optional reranker of the transformation stage (see
  [Query transformation reranker](#query-transformation-reranker)). The stored trace also carries one node per
  query, so the process output grows with the query count.

- **LLM stages are not resident simultaneously, but a nested retriever can
  exceed one model.** Each top-level stage's model is a lazy proxy: it loads
  when its stage starts and is closed as soon as the stage ends, so peak memory
  is the largest **top-level** stage — the generation model, the retriever LLM
  and the transformer are never resident at the same time. A **nested**
  agentic retriever can keep its parent and child evaluation LLMs live
  simultaneously, so peak can exceed one model in that configuration. The
  trade-off is reloading weights per turn/stage whenever the same checkpoint is
  used more than once. `context_window` still dominates the KV-cache footprint —
  a Phi-4-mini at a 20k-token window already spends ≈ 2.5 GiB — so a single
  large GGUF can still fail to fit. The GGUF loader raises an actionable error
  naming the model, device and context window and suggesting CPU, a lower
  `context_window` or a smaller checkpoint; llama.cpp's free-memory report in
  that error is best-effort. HuggingFace download/network failures are reported
  as download failures, not as insufficient memory, and a missing or partial
  GGUF file raises a file-specific "missing/incomplete, re-download" error.
  `is_downloaded` likewise requires a matching GGUF file on disk.

- **The pure factory path still builds nested LLMs eagerly.** Calling
  `RAGModelsFactory.create_retriever()` directly — or using `RetrieverFactory`
  on its own — resolves nested LLMs when the retriever is constructed instead of
  deferring them. The production path goes through `RetrieverSetupService`,
  which wraps each LLM stage in the lazy resolver, so use the setup service for
  VRAM-constrained deployments.

- **Lazy plugin LLMs must expose function-calling support on the class.** The
  lazy wrappers capture the capability from the component class, not from an
  instance, so a plugin LLM used lazily has to implement
  `supports_function_calling()` as a classmethod or set
  `SUPPORTS_FUNCTION_CALLING` on the class. An instance-only implementation is
  invisible to the wrapper.

- **GPU embedding models and cross-encoders are not released by the retriever
  close hooks.** The lazy lifecycle covers the stage LLMs; a dense embedding
  model or a GPU cross-encoder stays on the device for the life of the
  retriever. On a small GPU prefer the CPU variants for those components.

- **Nested LLM parameters are validated during assembly.** Deferring
  construction does not defer validation: a transformer's or retriever's nested
  LLM is checked against its `SCHEMA` while the pipeline is assembled, so bad
  parameters fail before any weights load.

## Concurrency

- **`get_or_create_chunk_set()`** uses a SELECT-then-INSERT pattern without a
  lock or upsert. `RAGChunkSet.signature` is UNIQUE, so a concurrent race
  cannot persist duplicate chunk sets; the losing request instead surfaces a
  database error (wrapped as `RuntimeError`).

- **SQLite foreign keys are not enforced.** The engine is created without
  `PRAGMA foreign_keys=ON` and nothing sets it per connection
  (`dependencies/database/sqlite_database.py`), so every `ondelete` clause in
  the models is documentation rather than behaviour. Cascading deletes have to
  come from SQLAlchemy relationships — which is why, for example,
  `GenerativeSession.document_links` carries `cascade="all, delete-orphan"`.

- **Huey consumer runs in-process.** In dev mode it spawns as a subprocess; in
  PyInstaller bundles it runs as a daemon thread. Both models limit
  parallelism.

- **`RAGJob` cleans up on every failure path.** Setup, generation and output
  persistence failures all release the pipeline models and clear the process
  progress before the job is marked errored, so a failed turn leaves neither
  loaded weights nor a stale progress payload behind.

## Prompt Wiring

- The query-transformation prompts (`Default`/`Custom` `QueryRewriting`,
  `QueryExpansion`, `QueryDecomposition`) and the `LLMQueryRewriter`,
  `LLMQueryExpander`, `LLMQueryDecomposer` components **are** wired: they are
  registered, validated by
  `services/RAG/query_transformation_validation.py`, and run by the pipeline.

## Query Transformation

- **Function-calling versus text route.** The stage uses constrained function
  calling only when the configured LLM reports support
  (`SUPPORTS_FUNCTION_CALLING`, true for the local GGUF text-generation base);
  every other model falls back to a tolerant text parser over the model's raw
  output. Output shape therefore depends on the model, not just the prompt.

- **A transformation failure fails the turn.** There is no silent fallback to
  the raw user message: if the model produces unparseable output, calls the
  wrong function, or the backend raises, the pipeline raises and the chat turn
  errors out.

- **The nested transformation and retrieval LLMs share the RAG LLM defaults.**
  The server-side override is `context_window=10000`, `max_tokens=300` and
  `temperature=0.1` (see `rag_llm_param_overrides()`). A value equal to the
  model schema's placeholder is treated as "not customized" and replaced; an
  explicit non-default value wins. LLMs that name the context window
  differently (for example DeepSeek's `n_ctx`) keep their own value.
  Sessions created before this default changed keep their stored parameters:
  clear the `context_window` field to pick up the new value.

- **Sessions created before the agentic retriever prompt changed keep their
  stored template.** The zero-based chunk-position rule is part of the default
  template; an existing session that already stores the previous template must
  clear the prompt template (or reselect the default agentic retriever prompt)
  to receive it.

- **Sessions created before the additional-chunk semantics keep their stored
  prompt template.** `call_retrievers` now means "fetch this many *additional*
  chunks from that retriever", not an absolute `top_k`; the default template
  states it, but a session that stored the older wording (or a forked
  `CustomAgenticRetrieverPrompt` with its own text) still asks the model for an
  absolute size. The retriever always interprets every value as an
  additional-chunk count and never migrates or rewrites stored templates, so
  such a session simply over- or under-fetches relative to what the model
  intended. Clear the prompt template (or reselect the default agentic retriever
  prompt) to adopt the new instructions.

- **An agentic child can contribute fewer chunks than requested.** The
  cumulative size is a hint: a child with a shorter usable prefix, or one that
  returns only identities the retriever already pooled, adds nothing that round.
  The trace records the real pool growth (`added: 0`), and the retriever neither
  retries nor fabricates chunks; `max_iters` bounds how long it keeps asking. An
  ensemble additionally clamps each per-child request to the slots the round can
  still fill, so a later child in the same round is never over-fetched. When a
  child over-returns or reorders its results, only the highest-ranked unseen
   identities of its response enter the pool, never the tail.

- **Discarding may not free a slot when the child over-returns.** The retrieval
  pool keeps returned chunks beyond its visible `max_chunks` prefix; discarding
  a visible chunk can expose one of those stored chunks instead of reducing the
  pool size. A later verdict that also calls a retriever can therefore be
  rejected for lack of capacity. Keep the child's configured result count at or
  below the agentic retriever's `max_chunks` when relying on discard-and-refill.

- **`prompt` and `llm_model` refs are mandatory.** A transformer is built only
  from an explicit prompt component and an explicit text-to-text model
  reference; neither has an implicit default.

## Query transformation reranker

The query-transformation stage has an optional `reranker` parameter. It is a
component field whose parent is the `ChunkScorer` capability, so the offered
components are the retrievers whose class inherits that interface (the dense,
sparse, cross-encoder, MMR, sequential and agentic-single/reranker retrievers).
The parallel and agentic-ensemble retrievers do not inherit it: they average
children that may score different chunks, so their scores are not comparable.
The default is the semantic retriever (multilingual paraphrase MiniLM L12 v2),
and `null` disables reranking.

The reranker orders the merged multi-query pool against the original user
message with its `score_chunks`, and keeps its `retrieval_top_k` (`ChunkScorer.rerank_chunks`). It is set up
through the same retriever setup as the retrieval stage, so it has the same
index infrastructure. Known limitations of the current implementation:

- **The reranking step is a trailing trace entry, shown only in the "All"
  view.** `RAGPipeline._rerank_pool()` appends
  `{"stage": "rerank", "reranker": <node>}` after the per-query entries. The
  node is a retriever trace node: `chunks` are the kept chunks and `pool` every
  candidate the reranker received. The entry has no `retriever`, so consumers that render
  per-query entries skip it, and the Pipeline panel draws it under the query
  trees only when no single query is selected. The node carries no per-chunk
  scores.

- **Every pooled chunk must be scorable.** A chunk without an id, or whose
  ids the reranker's index does not hold, makes the stage fail with
  `RAGRetrieverRerankError` (wrapped as a pipeline error) instead of being
  kept unranked, so the pool is never returned as if it had been ordered.

- **A retrieve-then-expand window is ranked by its best chunk.** A window has
  the id of its first covered chunk, but the reranker scores every stored chunk
  it spans (through `source_positions`) and ranks the window by the lowest
  distance among them. A scorer without the retriever's chunk store cannot
  resolve the covered ids and falls back to the window's own id.

- **Reranking cost grows with the pool, not with the corpus.** The reranker
  scores only the chunks of the merged pool: at most the number of queries
  times the retrieval stage's `top_k`, fewer once queries return the same
  chunk, and more when retrieve-then-expand windows are scored through every
  chunk they cover. For a cross-encoder reranker that is one model forward
  pass per pooled chunk on every turn. The context budget does not price it,
  because the budget only counts the tokens of the chunks that reach the
  generator. Building the chunk lookup the cross-encoder needs walks the whole
  corpus on each call, which is cheap next to that inference and only matters
  for very large corpora.

- **A reranker has its own index cost.** Its setup goes through the retriever
  setup, so it reuses a stored index only when the embedding and corpus
  identity match the retrieval stage. A reranker with a different embedding is
  indexed again. It is built together with the retriever stage, by the indexing
  run (`SetupService.build_index`, "Building the reranker" progress step), so
  the first chat turn after indexing no longer embeds the corpus silently.
  Composite rerankers reuse their stored composite row when the children are
  unchanged.

- **The rewriter has no reranker.** The `reranker` field lives on
  `MultiQueryTransformationSchema`, shared by decomposition and expansion. A
  rewrite emits one query and merges nothing, so there is no pool to reorder.
  Validation rejects a non-null `reranker` on a rewriter, and the setup never
  builds one for it.

- **An absent `reranker` key means "off" for stored sessions.** The default
  semantic reranker is injected only when a session is created. A session that
  stores a stage without the key keeps running without reranking, and an update
  that resends such a stage keeps it off (it never turns reranking, and its
  index, on silently). Send the key explicitly to enable it.

- **A stored decomposition without `max_subqueries` is not capped.** The
  schema placeholder and a new session suggest three sub-queries
  (`DEFAULT_MAX_SUBQUERIES`), but a stored stage that omits the key keeps
  running uncapped, and an update that resends the stage without it keeps it
  uncapped. An explicit `null` also means no limit; an explicit integer caps
  the result. The context budget prices an uncapped decomposition at the
  declared three queries, so it under-counts when the model emits more.

- **Cleanup tells the stages apart by their stored parameters.** The retriever
  stage and the reranker keep their rows in the same pipeline and one row can
  serve both. When either changes, the other's rows are protected, the
  reranker's rows are removed when only its configuration changes, and rows
  are matched by their stored parameters (class name alone is only the fallback
  for the retriever stage's own rows).

- **The context budget prices the reranker as a cap on units.** The reranker's
  `top_k` bounds how many units of the merged pool reach the prompt, and each
  unit is as wide as the retriever stage's retrieve-then-expand window; the
  reranker's own expansion options never widen the pool. An explicitly uncapped
  decomposition (`max_subqueries: null`) is priced at the reranker's cap when
  there is one; without a reranker it is still priced at the declared count
  although the model may emit more.

- **Transformation config errors are pipeline runtime errors by design.**
  `RAGTransformationError` (and therefore `RAGTransformationConfigError`)
  inherits from `RAGQueryTransformationError` → `RAGPipelineRuntimeError`
  instead of `RAGWorkflowError`, so existing `RAGPipelineRuntimeError` handlers
  keep catching the stage. Any such handler therefore also catches its
  configuration failures. The stage raises four types: the generic
  `RAGQueryTransformationError`, `RAGTransformationConfigError`,
  `RAGTransformationOutputError` (the model's output could not be parsed) and
  `RAGTransformationGenerationError` (the model call failed). Nothing in the
  backend catches them by subtype today: the job error message shows their
  text only, not their class, and no code retries an unparseable output or
  answers a configuration failure differently from a model failure. The
  subtypes exist so such handling can be added without parsing messages.

## Maintenance

- **After RAG model schema changes**, delete `sqlite.db` and the
  `~/.DashAI/rag/` directory to rebuild the database and chunk cache from
  scratch.

- **Tokenizer downloads on first use.** `TokenChunkModel` downloads the
  tokenizer from HuggingFace Hub lazily (on first `chunk_text()` call), but
  this still requires network access. Pre-download tokenizers for offline use.

- **Embedding models downloaded on first use.** Each `TextEmbeddingConverter`
  subclass downloads its checkpoint from HuggingFace Hub when the converter is
  first asked to encode text. Pre-download for offline environments.

## Code Duplication

- **`RAGJob` reimplements `GenerativeJob`'s status helpers.**
  `set_status_as_delivered()`, `set_status_as_error()`, and `get_job_name()`
  are near-duplicates that have already diverged: the RAG job clears
  `progress` on error and prefixes its job name with `RAG:`. `RAGJob` is a
  standalone `BaseJob` subclass (not a subclass of `GenerativeJob`), so the
  logic is copied rather than inherited. This is accepted technical debt; a
  future refactor should extract a shared mixin or base class.

## Deprecated Patterns

- The old `notebooks/`, `images/`, `explanations/` directories listed in the
  runtime data layout are no longer actively used by the RAG module.

- **The RAG embedding classes are gone (historical note).**
  `models/RAG/embeddings/` and its `DenseEmbedding` subclasses (`BERTEmbedding`,
  `DistilBERTEmbedding`, `E5Embedding`, `InstructorEmbedding`, `LaBSEmbedding`,
  `RoBERTaEmbedding`, `SentenceTransformerEmbedding`, `FastTextEmbedding`) were
  replaced by the text embedding converters in
  `converters/hugging_face/text_embedding/`. Dense retrieval now takes a
  `TextEmbeddingConverter` through `DenseEmbeddingRetriever.embedding_model`, and
  the sparse retrievers take a `BagOfWordsConverter` / `TFIDFConverter` through
  their `vectorizer` field. FastText/static embeddings have no replacement.

## Document Loaders

- **`PypdfDocumentDataLoader`** defaults to `strict=True`, rejecting malformed
  PDFs (xref errors). Use `strict=False` for broken PDFs. Parsing runs in
  `DocumentJob`, so a failure surfaces as an `ERROR` row (with its partial
  folder deleted) rather than a half-parsed document in the library.

## Document Upload

- **A folder upload is one `Folder` plus one `DataDocument` per file.** The
  batch endpoint has no hard file-count limit (the UI asks for confirmation
  above 100); each individual file is still capped at 4 GiB by the multipart
  job endpoint, and the whole file is parsed in memory by `DocumentJob`.
- **Subfolders are flattened.** The upload dialog keeps each file's relative
  path for display, but every file becomes a direct member of the requested
  folder; the `Folder` model has no parent link.
- **A failed parse leaves an `ERROR` document in Data.** It is never attached
  to the session; the progress panel reports it and the user can delete it from
  the Data module. A row renamed to avoid a duplicate name is reported in the
  upload summary.
- **Closing the upload dialog mid-run attaches only the documents that already
  finished.** The rest keep parsing in the background and stay in Data; they
  must be added later from "Add from Data". The dialog waits at most 10 s for
  that partial attach before closing.
- **SQLite foreign keys are still not enabled.** `folder_id` references are
  protected by an explicit write lock in the create/patch/delete paths, not by
  `PRAGMA foreign_keys`; any new code that writes `folder_id` outside
  `DocumentBatchService` or `PATCH /documents/{id}` must take the same lock.

## Validation

- **Parameters hash** only covers `rag_prompt` and `rag_generation_model`.
  `rag_chunking_model`, `rag_embedding_model`, and retriever tables still
  compare JSON columns directly — fragile to key ordering in SQLite.
- **Internal `rag_prompt` rows are not garbage-collected.** Rows written by
  `get_or_create` are keyed by `parameters_hash` and shared between sessions;
  they are marked `is_library=False` and are not exposed in the prompt library.
  They stay until a session deletion removes its `rag_pipeline` (the rows
  themselves remain, bounded by distinct templates).
- **Prompt deletion is explicit and audited.** `GET /api/v1/prompt/library`
  returns the user-created rows (`is_library=True`) and the built-in defaults
  (`is_library=False`, read-only). `DELETE /api/v1/prompt/{id}` only accepts
  `is_library=True` rows; internal pipeline rows and built-in defaults are
  refused. A library prompt used by a session returns `409` with
  the dependent sessions; `?cascade_sessions=true` deletes those sessions
  through `SessionDocumentService.delete_session()` before deleting the
  prompt. The FK cascade
  is still not trusted (SQLite foreign keys are off). A session counts as a
  dependent when a `rag_pipeline` points at the prompt, when its parameters
  carry a legacy `prompt_id`, or when its stored prompt component and template
  text match the library row. The last case ignores `language` and treats a
  copied template as a dependency, because that is how the session was seeded.
  If a user saves a template that already exists as an internal pipeline row,
  `POST /api/v1/prompt/` promotes that row to `is_library=True` and renames it
  instead of returning a duplicate error for a row the library did not show.

## Empty sessions

A RAG session is created with no documents, so several things have to cope with
an empty `documents` list:

- `IndexStatusService` reports a `no_documents` status, rather than promising an
  indexing run that cannot happen.
- `POST /generative-process/` refuses a chat turn on an empty RAG session. That
  guard is load-bearing: without it `SetupService.build_pipeline` would create a
  chunk set over zero documents and fit a retriever on nothing, failing opaquely
  inside the vectorizer.
