/** Registry parent of every retriever. */
export const RETRIEVER_PARENT = "BaseRetriever";

/** Registry parent of the retrievers that can score an already-retrieved pool. */
export const CHUNK_SCORER_PARENT = "ChunkScorer";

/**
 * Registry parents whose components the retriever fields render: every
 * retriever and every chunk scorer, composite or not.
 */
export const RETRIEVER_FIELD_PARENTS = [RETRIEVER_PARENT, CHUNK_SCORER_PARENT];
