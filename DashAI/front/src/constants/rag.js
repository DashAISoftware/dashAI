/**
 * Identifiers for the two inline views in the RAG message sources panel.
 */
export const TRACE_VIEW_CHUNKS = "chunks";
export const TRACE_VIEW_PIPELINE = "pipeline";

/**
 * `stage` value of the trace entry that records the pool reranking. Mirrors
 * `TRACE_STAGE_RERANK` in the backend `RAG_constants.py`.
 */
export const TRACE_STAGE_RERANK = "rerank";

/**
 * Params of a query transformer that the stage code reads or writes by name.
 * `MAX_SUBQUERIES_KEY` and `RERANKER_KEY` mirror the backend `RAG_constants.py`.
 */
export const LLM_MODEL_KEY = "llm_model";
export const PROMPT_KEY = "prompt";
export const MAX_SUBQUERIES_KEY = "max_subqueries";
export const RERANKER_KEY = "reranker";

/** Variant of the prompt a freshly enabled stage starts from. */
export const PROMPT_VARIANT_DEFAULT = "default";

/** Language a prompt template falls back to when none is stored. */
export const DEFAULT_PROMPT_LANGUAGE = "en";

/** JSON-schema `type` values the component forms read. */
export const SCHEMA_TYPE_OBJECT = "object";
export const SCHEMA_TYPE_ARRAY = "array";
export const SCHEMA_TYPE_NULL = "null";

/** Placeholder property that marks a schema field as an optimizer field. */
export const OPTIMIZE_PLACEHOLDER_KEY = "optimize";

/** Component name of a tree node that was added but not configured yet. */
export const EMPTY_COMPONENT_NAME = "";
