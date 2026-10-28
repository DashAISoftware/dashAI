# RAG Module Overview

## What is RAG in DashAI

Retrieval-Augmented Generation (RAG) lets users upload documents and have
conversations with them. The pipeline retrieves relevant document chunks for
each user query and feeds them to an LLM as context, producing grounded
answers that cite the source material.

## Pipeline Stages

Four fixed stages plus an optional pre-retrieval query transformation stage:

```
User query
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│        0. Query Transformation (optional)                 │
│   Turn the message and the last `history_window` prior   │
│   messages into one or more search queries:              │
│     • LLMQueryRewriter     — 1-to-1 rewriting            │
│     • LLMQueryExpander     — 1-to-n expansion            │
│     • LLMQueryDecomposer   — 1-to-n decomposition        │
│   When disabled, the message itself is the only query.   │
└──────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                  1. Document Loading                      │
│   Load the parsed Data-module documents (txt, pdf, md,   │
│   csv, rst, tex) and build in-memory RAGDocument objects │
│   that keep the Text items and map offsets back to pages. │
└──────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                  2. Chunking                              │
│   Split each document into smaller pieces using one of:  │
│     • CharacterChunkModel    — fixed-size char windows   │
│     • TokenChunkModel        — token-aware splitting     │
│     • RecursiveCharacterChunk — separator-priority split │
│   Chunks are persisted to the DB and cached by SHA-256   │
│   signature for reuse within the session. Fitted state   │
│   (sparse matrices, embedding matrices) is content-      │
│   addressed and reused across sessions.                  │
└──────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                  3. Retrieval                             │
│   Retrieve every query independently, then merge the     │
│   ranked lists round-robin and de-duplicate by           │
│   (document_id, document_position):                      │
│     • Sparse retrievers    — TF-IDF, BM25                │
│     • Dense retrievers     — embedding-based similarity  │
│     • Composite retrievers — Sequential, Parallel, MMR   │
│   (Composite pattern: leaf + composite nodes)            │
│   Every retriever returns (chunks, trace).               │
└──────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│                  4. Generation                            │
│   Inject chunks (and, when the transformation stage      │
│   ran, the queries) into a prompt template and generate  │
│   a response via an LLM. Supports multi-language prompts │
│   (en/es/pt) and custom templates.                       │
└──────────────────────────────────────────────────────────┘
     │
     ▼
   Five typed output rows: Queries, Dict (chunks), Trace, Timings, str (answer)
```

## Code Location

| Layer                           | Path                                                                                                                                                                                             |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Services                        | `DashAI/back/services/RAG/`                                                                                                                                                                      |
| Pipeline                        | `DashAI/back/models/RAG/RAG_pipeline.py`                                                                                                                                                         |
| Factory                         | `DashAI/back/models/RAG/RAG_models_factory.py`                                                                                                                                                   |
| Sub-factories                   | `DashAI/back/models/RAG/llm_factory.py`, `prompts/prompt_factory.py`, `chunking_models/chunking_model_factory.py`, `retrievers/retriever_factory.py`, `transformation/transformation_factory.py` |
| Query transformation            | `DashAI/back/models/RAG/transformation/`                                                                                                                                                         |
| Transformation prompts          | `DashAI/back/models/RAG/prompts/transformation/`                                                                                                                                                 |
| Query transformation validation | `DashAI/back/services/RAG/query_transformation_validation.py`                                                                                                                                    |
| Constants                       | `DashAI/back/models/RAG/RAG_constants.py`                                                                                                                                                        |
| Utilities                       | `DashAI/back/models/RAG/utils.py`                                                                                                                                                                |
| Exceptions                      | `DashAI/back/models/RAG/exceptions/`                                                                                                                                                             |
| Retrievers                      | `DashAI/back/models/RAG/retrievers/` (subdirs: `dense/`, `sparse/`, `composite/`, `cross_encoder/`)                                                                                              |
| Chunking                        | `DashAI/back/models/RAG/chunking_models/`                                                                                                                                                        |
| Prompts                         | `DashAI/back/models/RAG/prompts/` (subdirs: `generation/`, `augmentation/`, `transformation/`)                                                                                                   |
| Documents                       | `DashAI/back/models/RAG/documents/`                                                                                                                                                              |
| Embeddings                      | `DashAI/back/converters/hugging_face/text_embedding/` (dense vectors) and `DashAI/back/converters/scikit_learn/` (`bag_of_words.py`, `tf_idf.py`)                                                |
| Jobs                            | `DashAI/back/job/RAG_job.py`                                                                                                                                                                     |
| Task                            | `DashAI/back/tasks/RAG_task.py`                                                                                                                                                                  |
| Core                            | `DashAI/back/core/component_validation.py`                                                                                                                                                       |
| Frontend pages                  | `DashAI/front/src/pages/generative/RAG/` (entry point, creation) and `pages/generative/RAGSession/` (the session view)                                                                           |
| Frontend components             | `DashAI/front/src/components/generative/RAG/`                                                                                                                                                    |

## Quick Architecture

```
Browser / PyWebView
  → React (port 3000)
    → POST /api/v1/generative-session/   (create session)
      → Validate payload, components, documents, prompt, optional transformer
    → POST /api/v1/generative-process/   (create process)
    → POST /api/v1/job/                  (enqueue job)
      → Huey Job Queue
        → RAGJob.run()
          → SetupService.build_pipeline()
            → DocumentService → ChunkingService → RetrieverSetupService
            → LLMService → PromptService → TransformationFactory (optional)
            → RAGPipeline.generate()
              → [query transformation] → per-query retrieval → round-robin merge
              → prompt (optional {queries}) → LLM generation
          → RAGTask.process_output() → Queries, Dict, Trace, Timings, str rows
        → Frontend polls the process:
          GET /api/v1/generative-process/session/{id}
```

## Component Types

- **Chunking models** — Character, Token, Recursive character (all implement
  `BaseChunkingModel`)
- **Retrievers** — `BaseRetriever` base; Sparse (TF-IDF, BM25), Dense (via
  `TextEmbeddingConverter` subclasses), Cross-Encoder (SentenceTransformer
  re-rankers), Composite (Sequential, Parallel, MMR Reranker, LLM-evaluated
  depth and ensemble)
- **Query transformations** — `BaseQueryTransformation` base; LLM-backed
  transformers (`LLMQueryRewriter`, `LLMQueryExpander`, `LLMQueryDecomposer`)
  that turn the user message into one or more search queries before retrieval
- **Prompts** — Generation prompts (Default, Custom, QA) in en/es/pt;
  query transformation prompts (Rewriting, Expansion, Decomposition, each
  Default + Custom); augmentation prompts (Default, Custom) are registered but
  not wired into the pipeline
- **LLMs** — GGUF chat checkpoints (Llama, Mistral, Mixtral, Qwen, SmolLM,
  Phi-4) plus any other `TextToTextGenerationTaskModel` registered in the
  component registry
- **Embeddings** — Registered `TextEmbeddingConverter` converters (Advanced
  Preprocessing), one per checkpoint: MiniLM, mpnet, multi-qa MiniLM/mpnet,
  paraphrase-multilingual MiniLM/mpnet, LaBSE, multilingual E5 (small, base,
  large), Qwen3-Embedding 0.6B, harrier-oss-v1 (270m, 0.6b) and
  instructor-large. `TextEmbeddingConverter` is the shared base class. The sparse
  side uses `BagOfWordsConverter` / `TFIDFConverter` (`SparseTextVectorizer`).

## Available Models

### Chunking Models

| Class                          | Model names                            | File                                                                        |
| ------------------------------ | -------------------------------------- | --------------------------------------------------------------------------- |
| `CharacterChunkModel`          | — (fixed character count chunking)     | `DashAI/back/models/RAG/chunking_models/character_chunk_model.py`           |
| `RecursiveCharacterChunkModel` | — (recursive separator-based chunking) | `DashAI/back/models/RAG/chunking_models/recursive_character_chunk_model.py` |
| `TokenChunkModel`              | — (fixed token count chunking)         | `DashAI/back/models/RAG/chunking_models/token_chunk_model.py`               |

### Embedding Models

Every embedding model is a `TextEmbeddingConverter` converter under
`DashAI/back/converters/hugging_face/text_embedding/`, one subclass per
checkpoint. All of them are registered in `initial_components.py` through
`TEXT_EMBEDDING_CONVERTERS`
(`converters/hugging_face/text_embedding/__init__.py`).

| Class                                        | Model name                                                    | File                                                                         |
| -------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `AllMiniLML6V2Embedding`                     | `sentence-transformers/all-MiniLM-L6-v2`                      | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `AllMpnetBaseV2Embedding`                    | `sentence-transformers/all-mpnet-base-v2`                     | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `MultiQAMiniLML6CosV1Embedding`              | `sentence-transformers/multi-qa-MiniLM-L6-cos-v1`             | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `MultiQAMpnetBaseCosV1Embedding`             | `sentence-transformers/multi-qa-mpnet-base-cos-v1`            | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `ParaphraseMultilingualMiniLML12V2Embedding` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `ParaphraseMultilingualMpnetBaseV2Embedding` | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `LaBSEEmbedding`                             | `sentence-transformers/LaBSE`                                 | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `MultilingualE5SmallEmbedding`               | `intfloat/multilingual-e5-small`                              | `DashAI/back/converters/hugging_face/text_embedding/e5.py`                   |
| `MultilingualE5BaseEmbedding`                | `intfloat/multilingual-e5-base`                               | `DashAI/back/converters/hugging_face/text_embedding/e5.py`                   |
| `MultilingualE5LargeEmbedding`               | `intfloat/multilingual-e5-large`                              | `DashAI/back/converters/hugging_face/text_embedding/e5.py`                   |
| `InstructorLargeEmbedding`                   | `hkunlp/instructor-large`                                     | `DashAI/back/converters/hugging_face/text_embedding/instructor.py`           |
| `Qwen3Embedding06B`                          | `Qwen/Qwen3-Embedding-0.6B`                                   | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `HarrierOSS270MEmbedding`                    | `microsoft/harrier-oss-v1-270m`                               | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |
| `HarrierOSS06BEmbedding`                     | `microsoft/harrier-oss-v1-0.6b`                               | `DashAI/back/converters/hugging_face/text_embedding/sentence_transformer.py` |

`TextEmbeddingConverter` is the shared base; `SentenceTransformerTextEmbedding`,
`E5TextEmbedding` and `InstructorTextEmbedding` sit between it and the
checkpoint subclasses and supply the query/passage prompts (E5 prepends
`query:`/`passage:`, instructor applies its `instruction`, Qwen3 and harrier
prepend a query-only instruction).

The two sparse vectorizers the sparse retrievers nest are converters as well:
`BagOfWordsConverter` (`converters/scikit_learn/bag_of_words.py`) and
`TFIDFConverter` (`converters/scikit_learn/tf_idf.py`), both subclasses of
`SparseTextVectorizer` (`converters/scikit_learn/text_vectorizer.py`).

### Retriever Models

| Class                                      | Model names                                                      | File                                                                                    |
| ------------------------------------------ | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `BM25Retriever`                            | — (BM25 algorithm)                                               | `DashAI/back/models/RAG/retrievers/sparse/bm25_retriever.py`                            |
| `TFIDFRetriever`                           | — (TF-IDF algorithm)                                             | `DashAI/back/models/RAG/retrievers/sparse/tfidf_retriever.py`                           |
| `DenseEmbeddingRetriever`                  | Uses any `TextEmbeddingConverter` from above                     | `DashAI/back/models/RAG/retrievers/dense/dense_embedding_retriever.py`                  |
| `MMRRerankerRetriever`                     | — (MMR reranker over nested retrievers)                          | `DashAI/back/models/RAG/retrievers/composite/mmr_reranker_retriever.py`                 |
| `SequentialRetriever`                      | — (executes retrievers sequentially)                             | `DashAI/back/models/RAG/retrievers/composite/sequential_retriever.py`                   |
| `ParallelRetriever`                        | — (executes retrievers in parallel and merges)                   | `DashAI/back/models/RAG/retrievers/composite/parallel_retriever.py`                     |
| `LLMEvaluatedDepthRetriever`               | — (LLM-judged adaptive depth over one child)                     | `DashAI/back/models/RAG/retrievers/composite/llm_evaluated_depth_retriever.py`          |
| `LLMEvaluatedEnsembleRetriever`            | — (LLM-chosen children across rounds)                            | `DashAI/back/models/RAG/retrievers/composite/llm_evaluated_ensemble_retriever.py`       |
| `SentenceTransformerCrossEncoderRetriever` | 17 cross-encoder models from `cross-encoder/*` (see table below) | `DashAI/back/models/RAG/retrievers/cross_encoder/sentence_transformer_cross_encoder.py` |

Both sparse retrievers take a nested `vectorizer` component selected in their
params: `BM25Retriever` requires a `BagOfWordsConverter` and `TFIDFRetriever` a
`TFIDFConverter` (`component_field` restricts each to its own parent).

The two `LLMEvaluated*` retrievers ask their configured model for a structured
sufficiency verdict: the depth retriever evaluates after every round except the
final one, while the ensemble retriever also makes a planning call before the
first round. When the model supports function calling, the verdict is obtained
through `generate_function_call` using the retriever's function schema
(constrained by the backend); otherwise the prompt is answered as text and
parsed by the tolerant text parser. Both routes share the same tolerant
contract: an invalid operation inside a verdict is dropped individually, valid
ones are preserved, and only a verdict with no usable operation left (or an
invalid `sufficient` field) is rejected. An insufficient verdict has three
optional action fields — `call_retrievers`, `request_specific_chunks` and
`discard_specific_chunks` — and at least one valid operation must remain.
llama.cpp's GBNF converter enforces `type`, `required` and
`minItems` but not numeric `minimum`, so the runtime validator remains the
authoritative guard for `top_k >= 1` and chunk positions `>= 0`.

Both retrievers share the `function_call_max_trials` parameter (default `3`,
capped at `10`), the maximum number of evaluation attempts including the first.
An unusable verdict with no valid operation left is retried on **both** the
function-calling and text routes until the limit is reached, then the stage
fails loudly.

#### Retrieve then expand

Every retriever schema inherits two fields from `RetrievalExpansionSchema`
(`DashAI/back/models/RAG/retrievers/retrieval_expansion.py`):
`enable_retrieve_then_expand` (default `false`) and `expand_window` (default
`3`, accepted range `1..32`). When enabled, the retriever keeps its retrieval
and — in a composite — its merge/re-rank untouched and widens only its **final**
output: each plain retrieved chunk is replaced by a window of `expand_window`
stored chunks centred on it. Odd values are centred exactly on the retrieved
chunk; even values keep the extra chunk after it; the window start is clamped to
the document so a document with enough chunks always yields a full window. The
window is resolved in document-position space, so a chunker whose positions are
not `0..n-1` never drags in chunks from outside the window. Both fields are
strictly validated (`bool` and real `int`), in the schema *and* in the retriever
constructor, because composites are built without schema validation.

Windows that overlap are merged into one unit whose text concatenates the
covered chunks; the unit keeps the `id`, `page` and `document_position` of its
first covered chunk and records every covered position in
`Chunk.source_positions`, so the trace references the window's first
`"<document_id>_<document_position>"` key. A chunk that already carries
`source_positions` — one that a child retriever expanded — is a **fixed** window:
it is never widened again, but it is merged with every unit it overlaps, so a
mix of plain and expanded chunks collapses correctly. A *plain* chunk whose
position is covered by an expanded unit is absorbed by it instead of being
repeated next to it, which is what keeps `merge_expanded_chunks` free of
duplicated text.

Expansion runs one last time over the merged results of all queries in
`RAGPipeline.multi_query_retrieval` (`BaseRetriever.merge_expanded_chunks`),
because two queries can return overlapping expanded windows that share no chunk
key and would otherwise repeat text in the prompt. The overlap merge also runs
in a composite whose own flag is off, so expanded children never hand
overlapping units to a nested re-ranker; only the widening step is gated by the
option. When two units share an anchor position, the one covering more chunks
wins, in the pipeline merge and in `ParallelRetriever`.

The options are **post-processing only**, so they are excluded from every
identity: the content-addressed sparse folder, the retriever table's natural key,
the index-status "already fitted" check, the cleanup decision and the preset
match all ignore them (recursively, children included). Toggling expansion
therefore reuses the existing index instead of re-embedding or re-fitting it, and
a legacy session without the fields still matches its preset. Retriever rows
written before this separation still store the old option keys inside their
parameters, so such a session may re-fit once after the upgrade; no migration is
performed. The context budget does account for the options: a capped retriever
is priced with the widest window in its subtree, and a composite without a cap
sums its expansion-aware children.

Two sessions indexing the same documents the same way also share the *fitted*
state: `services/RAG/utils.build_corpus_content_hash` hashes the corpus content
(document ids, chunk positions and chunk text hashes — never chunk database ids)
and the sparse folder and embedding-matrix folder names are derived from it plus
the chunking configuration and the parameters that shape them. `chunk_set_id`
and `session_id` are not part of those paths, so the second session loads the
first one's sparse matrix (rebound to its own chunk ids) and its
`embeddings.npy` instead of recomputing them. Cleanup deletes such a folder only
when the last row referencing it goes away.

Note that an expanded unit's `id` identifies its **first** covered chunk. When a
re-ranker (cross-encoder, MMR, sequential cascade) receives expanded candidates,
its per-chunk scoring therefore applies to that first chunk. **Recommended:**
enable expansion on the outermost retriever only — re-ranking then works on real
chunks and expansion stays final.

### Model Type Classification

**Bi-encoders** encode queries and documents independently into dense vectors, then
compare via cosine or dot-product similarity. **Cross-encoders** process
query-document pairs jointly through a single transformer forward pass, producing a
relevance score directly — they are used as _re-rankers_ on top of a fast first-stage
retriever. **Sparse retrievers** (BM25, TF-IDF) use statistical frequency-based
scoring.

**Ranker vs. reranker configuration.** In a two-stage retrieval setup the
first-stage retriever (the _ranker_) decides how many candidates are
fetched — this is configured on the child retriever itself via its own
`top_k`. The re-ranker (e.g. `SentenceTransformerCrossEncoderRetriever`
or `MMRRerankerRetriever`) then re-scores those candidates and returns
the top `top_k` of them. Re-rankers expose `top_k` plus their own model
parameters (e.g. `model_name` for the SentenceTransformer cross-encoder);
they have no `retrieval_factor`.

| Model Name                                                    | Type                           | Reference                                                                            |
| ------------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------ |
| **E5 family**                                                 |                                |                                                                                      |
| `intfloat/multilingual-e5-large`                              | Bi-encoder                     | https://huggingface.co/intfloat/multilingual-e5-large                                |
| `intfloat/multilingual-e5-base`                               | Bi-encoder                     | https://huggingface.co/intfloat/multilingual-e5-base                                 |
| `intfloat/multilingual-e5-small`                              | Bi-encoder                     | https://huggingface.co/intfloat/multilingual-e5-small                                |
| **Instructor family**                                         |                                |                                                                                      |
| `hkunlp/instructor-large`                                     | Bi-encoder (instruction-tuned) | https://huggingface.co/hkunlp/instructor-large                                       |
| **LaBSE**                                                     |                                |                                                                                      |
| `sentence-transformers/LaBSE`                                 | Bi-encoder                     | https://huggingface.co/sentence-transformers/LaBSE                                   |
| **Microsoft Harrier**                                         |                                |                                                                                      |
| `microsoft/harrier-oss-v1-270m`                               | Bi-encoder                     | https://huggingface.co/microsoft/harrier-oss-v1-270m                                 |
| `microsoft/harrier-oss-v1-0.6b`                               | Bi-encoder                     | https://huggingface.co/microsoft/harrier-oss-v1-0.6b                                 |
| **Qwen3 Embedding**                                           |                                |                                                                                      |
| `Qwen/Qwen3-Embedding-0.6B`                                   | Bi-encoder                     | https://huggingface.co/Qwen/Qwen3-Embedding-0.6B                                     |
| **Sentence-Transformers (general)**                           |                                |                                                                                      |
| `sentence-transformers/all-MiniLM-L6-v2`                      | Bi-encoder                     | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2                        |
| `sentence-transformers/all-mpnet-base-v2`                     | Bi-encoder                     | https://huggingface.co/sentence-transformers/all-mpnet-base-v2                       |
| **Sentence-Transformers (multi-qa)**                          |                                |                                                                                      |
| `sentence-transformers/multi-qa-mpnet-base-cos-v1`            | Bi-encoder                     | https://huggingface.co/sentence-transformers/multi-qa-mpnet-base-cos-v1              |
| `sentence-transformers/multi-qa-MiniLM-L6-cos-v1`             | Bi-encoder                     | https://huggingface.co/sentence-transformers/multi-qa-MiniLM-L6-cos-v1               |
| **Sentence-Transformers (multilingual)**                      |                                |                                                                                      |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Bi-encoder                     | https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2   |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | Bi-encoder                     | https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2   |
| **SentenceTransformers Cross-Encoders (re-rankers)**          |                                |                                                                                      |
| `cross-encoder/ms-marco-MiniLM-L-6-v2`                        | Cross-encoder                  | https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2                          |
| `cross-encoder/ms-marco-MiniLM-L-12-v2`                       | Cross-encoder                  | https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-12-v2                         |
| `cross-encoder/ms-marco-MiniLM-L-4-v2`                        | Cross-encoder                  | https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-4-v2                          |
| `cross-encoder/ms-marco-TinyBERT-L-2-v2`                      | Cross-encoder                  | https://huggingface.co/cross-encoder/ms-marco-TinyBERT-L-2-v2                        |
| `cross-encoder/ms-marco-electra-base`                         | Cross-encoder                  | https://huggingface.co/cross-encoder/ms-marco-electra-base                           |
| `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`                  | Cross-encoder (multilingual)   | https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1                    |
| `cross-encoder/stsb-roberta-base`                             | Cross-encoder                  | https://huggingface.co/cross-encoder/stsb-roberta-base                               |
| `cross-encoder/stsb-distilroberta-base`                       | Cross-encoder                  | https://huggingface.co/cross-encoder/stsb-distilroberta-base                         |
| `cross-encoder/stsb-TinyBERT-L-4`                             | Cross-encoder                  | https://huggingface.co/cross-encoder/stsb-TinyBERT-L-4                               |
| `cross-encoder/stsb-roberta-large`                            | Cross-encoder                  | https://huggingface.co/cross-encoder/stsb-roberta-large                              |
| `cross-encoder/quora-distilroberta-base`                      | Cross-encoder                  | https://huggingface.co/cross-encoder/quora-distilroberta-base                        |
| `cross-encoder/quora-roberta-base`                            | Cross-encoder                  | https://huggingface.co/cross-encoder/quora-roberta-base                              |
| `cross-encoder/nli-distilroberta-base`                        | Cross-encoder                  | https://huggingface.co/cross-encoder/nli-distilroberta-base                          |
| `cross-encoder/nli-roberta-base`                              | Cross-encoder                  | https://huggingface.co/cross-encoder/nli-roberta-base                                |
| `cross-encoder/nli-deberta-v3-base`                           | Cross-encoder                  | https://huggingface.co/cross-encoder/nli-deberta-v3-base                             |
| `cross-encoder/nli-MiniLM2-L6-H768`                           | Cross-encoder                  | https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768                             |
| `cross-encoder/nli-deberta-v3-xsmall`                         | Cross-encoder                  | https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall                           |
| `SentenceTransformerCrossEncoderRetriever`                    | Re-ranker (composite)          | Uses any cross-encoder model above + a child retriever                               |
| **Sparse Retrievers**                                         |                                |                                                                                      |
| `BM25Retriever`                                               | Statistical (sparse)           | https://en.wikipedia.org/wiki/Okapi_BM25                                             |
| `TFIDFRetriever`                                              | Statistical (sparse)           | https://scikit-learn.org/stable/modules/feature_extraction.html#tfidf-term-weighting |
| **Composite Retrievers**                                      |                                |                                                                                      |
| `MMRRerankerRetriever`                                        | Re-ranker (composite)          | https://en.wikipedia.org/wiki/Maximal_marginal_relevance                             |
| `SequentialRetriever`                                         | Pipeline (composite)           | —                                                                                    |
| `ParallelRetriever`                                           | Ensemble (composite)           | —                                                                                    |
| `LLMEvaluatedDepthRetriever`                                  | Adaptive depth (composite)     | Uses any `TextToTextGenerationTaskModel` from above                                  |
| `LLMEvaluatedEnsembleRetriever`                               | Adaptive ensemble (composite)  | Uses any `TextToTextGenerationTaskModel` from above                                  |
| **Dense Retriever**                                           |                                |                                                                                      |
| `DenseEmbeddingRetriever`                                     | Bi-encoder + search index      | Uses any text embedding converter from above                                         |

### Query Transformation Models

| Class                | Technique / parameters                                                                                                     | File                                                     |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `LLMQueryRewriter`   | rewriting (always one query); `prompt`, `llm_model`, `history_window` (default 2), `function_call_max_trials` (default 3, max 10)  | `DashAI/back/models/RAG/transformation/rewriting.py`     |
| `LLMQueryExpander`   | expansion (up to `n_queries`, default 3); `prompt`, `llm_model`, `history_window`, `function_call_max_trials` (default 3, max 10)  | `DashAI/back/models/RAG/transformation/expansion.py`     |
| `LLMQueryDecomposer` | decomposition (`max_subqueries` optional); `prompt`, `llm_model`, `history_window`, `function_call_max_trials` (default 3, max 10) | `DashAI/back/models/RAG/transformation/decomposition.py` |

All three share the base schema (`prompt`, `llm_model`, `history_window`,
`function_call_max_trials` default 3, max 10); expansion adds `n_queries` and
decomposition adds `max_subqueries`. `function_call_max_trials` only affects the
function-calling route described below. They route through function calling when
the configured model supports it, otherwise through a tolerant text parser. The
base contract
(`BaseQueryTransformation.transform(message, history)`) lives in
`DashAI/back/models/RAG/transformation/base_query_transformation.py` and the
shared LLM implementation in `.../llm_query_transformation.py`.

### Query Transformation Prompts

| Class                             | Technique / placeholders                                                          | File                                                                                  |
| --------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `QueryTransformationPrompt`       | base contract; required `{input}`, `{history}`                                    | `DashAI/back/models/RAG/prompts/transformation/transformation_prompt.py`              |
| `QueryRewritingPrompt`            | rewriting anchor; required `{input}`, `{history}`                                 | `DashAI/back/models/RAG/prompts/transformation/transformation_prompt.py`              |
| `QueryExpansionPrompt`            | expansion anchor; required `{input}`, `{history}`, `{n}`                          | `DashAI/back/models/RAG/prompts/transformation/transformation_prompt.py`              |
| `QueryDecompositionPrompt`        | decomposition anchor; required `{input}`, `{history}`, optional `{n_max}`         | `DashAI/back/models/RAG/prompts/transformation/transformation_prompt.py`              |
| `DefaultQueryRewritingPrompt`     | rewriting default (en/es/pt); required `{input}`, `{history}`                     | `DashAI/back/models/RAG/prompts/transformation/default_query_rewriting_prompt.py`     |
| `CustomQueryRewritingPrompt`      | rewriting custom; required `{input}`, `{history}`                                 | `DashAI/back/models/RAG/prompts/transformation/custom_query_rewriting_prompt.py`      |
| `DefaultQueryExpansionPrompt`     | expansion default (en/es/pt); required `{input}`, `{history}`, `{n}`              | `DashAI/back/models/RAG/prompts/transformation/default_query_expansion_prompt.py`     |
| `CustomQueryExpansionPrompt`      | expansion custom; required `{input}`, `{history}`, `{n}`                          | `DashAI/back/models/RAG/prompts/transformation/custom_query_expansion_prompt.py`      |
| `DefaultQueryDecompositionPrompt` | decomposition default (en/es/pt); required `{input}`, `{history}`, opt. `{n_max}` | `DashAI/back/models/RAG/prompts/transformation/default_query_decomposition_prompt.py` |
| `CustomQueryDecompositionPrompt`  | decomposition custom; required `{input}`, `{history}`, optional `{n_max}`         | `DashAI/back/models/RAG/prompts/transformation/custom_query_decomposition_prompt.py`  |

### Generation Prompts

| Class                          | Placeholders                                                        | File                                                                            |
| ------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `RAGGenerationPrompt`          | base contract; required `{input}`, `{chunks}`, optional `{queries}` | `DashAI/back/models/RAG/prompts/generation/RAG_generation_prompt.py`            |
| `DefaultRAGGenerationPrompt`   | default (en/es/pt)                                                  | `DashAI/back/models/RAG/prompts/generation/default_RAG_generation_prompt.py`    |
| `CustomRAGGenerationPrompt`    | user-defined template                                               | `DashAI/back/models/RAG/prompts/generation/custom_RAG_generation_prompt.py`     |
| `DefaultQARAGGenerationPrompt` | QA variant (en/es/pt)                                               | `DashAI/back/models/RAG/prompts/generation/default_QA_RAG_generation_prompt.py` |

The optional `{queries}` placeholder is filled with the queries the retrieval
stage ran over (joined with `"; "`); when the transformation stage is disabled
its whole line is removed from the rendered prompt.

### LLM Models (Text-to-Text Generation)

All registered LLMs are GGUF checkpoints loaded through llama.cpp, with the
repo and quantization fixed per class (except `Phi4MiniInstructModel`, which
takes them as parameters):

| Class                      | Checkpoint (quantization)                                    | File                                                                         |
| -------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| `Llama31_8BInstruct`       | `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` (Q4_K_M)         | `DashAI/back/models/hugging_face/llama_model.py`                             |
| `Llama32_1BInstruct`       | `bartowski/Llama-3.2-1B-Instruct-GGUF` (Q4_K_M)              | `DashAI/back/models/hugging_face/llama_model.py`                             |
| `Llama32_3BInstruct`       | `bartowski/Llama-3.2-3B-Instruct-GGUF` (Q4_K_M)              | `DashAI/back/models/hugging_face/llama_model.py`                             |
| `Mistral7BInstructV03`     | `bartowski/Mistral-7B-Instruct-v0.3-GGUF` (Q4_K_M)           | `DashAI/back/models/hugging_face/mistral_model.py`                           |
| `MistralNemoInstruct2407`  | `bartowski/Mistral-Nemo-Instruct-2407-GGUF` (Q4_K_M)         | `DashAI/back/models/hugging_face/mistral_model.py`                           |
| `Mixtral8x7BInstructQ4KM`  | `mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF` (Q4_K_M)      | `DashAI/back/models/hugging_face/mixtral_model.py`                           |
| `Mixtral8x7BInstructQ2K`   | `mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF` (Q2_K)        | `DashAI/back/models/hugging_face/mixtral_model.py`                           |
| `Qwen25_05BInstruct`       | `Qwen/Qwen2.5-0.5B-Instruct-GGUF` (Q8_0)                     | `DashAI/back/models/hugging_face/qwen_model.py`                              |
| `Qwen25_15BInstruct`       | `Qwen/Qwen2.5-1.5B-Instruct-GGUF` (Q8_0)                     | `DashAI/back/models/hugging_face/qwen_model.py`                              |
| `SmolLM2_360MInstruct`     | `HuggingFaceTB/SmolLM2-360M-Instruct-GGUF` (q8_0)            | `DashAI/back/models/hugging_face/smol_lm_model.py`                           |
| `SmolLM2_17BInstruct`      | `HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF` (q4_k_m)          | `DashAI/back/models/hugging_face/smol_lm_model.py`                           |
| `Phi4MiniInstructModel`    | `unsloth/Phi-4-mini-instruct-GGUF` (Q8_0), both as parameters | `DashAI/back/models/hugging_face/phi_4_mini_instruct_model.py`               |

`DeepSeekModel` (`hugging_face/deep_seek_model.py`) exists but is not registered
in `get_initial_components()`, so it is not offered in the UI.
