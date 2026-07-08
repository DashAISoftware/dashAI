# Known Limitations and Operational Notes

## Performance Constraints

- **Chunk similarity matrices are held in RAM.** This works for low hundreds of documents but will not scale to millions. No out-of-core or approximate indexing is used.
- **No streaming.** The frontend waits for the full LLM response before displaying it. Streaming support is not implemented.
- **No FAISS or HNSW indexing.** Dense retrieval performs O(n*dim) brute-force similarity search per query. For large document collections this will be slow.
- **DB session held open during LLM inference.** The same database transaction remains open while the LLM generates a response, which risks connection timeout on slow LLM calls.

## Concurrency

- `get_or_create_chunk_set()` uses a SELECT-then-INSERT pattern without a lock or upsert. This is safe for single-user usage but could create duplicate chunk sets under concurrent requests.

## Unused Components

- **`AugmentationPrompt`** components exist in the registry but are not yet wired into the pipeline. These are intended for future query-expansion / HyDE-style augmentation.

## Maintenance

- **After RAG model schema changes**, delete `sqlite.db` and the `~/.DashAI/rag/` directory to rebuild the database and chunk cache from scratch.
