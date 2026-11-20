import { getRetrieverComponents } from "../../../api/rag";

// Cached membership name-sets, populated once by loadRetrieverKinds().
let kinds = null;

/**
 * Load (once) retriever kind membership from the backend component hierarchy:
 * composite (children of CompositeRetriever) and embedding (children of
 * TextEmbeddingConverter).
 * @returns {Promise<{composite: Set<string>, embedding: Set<string>}>}
 */
export async function loadRetrieverKinds() {
  if (kinds) return kinds;
  let composite = [];
  let embedding = [];
  try {
    [composite, embedding] = await Promise.all([
      getRetrieverComponents("CompositeRetriever"),
      getRetrieverComponents("TextEmbeddingConverter"),
    ]);
  } catch (error) {
    // Degrade gracefully: empty sets mean isComposite/isEmbedding
    // return false and the UI falls back to ungrouped options instead of
    // hanging in a loading state forever.
    console.warn("Failed to load retriever kinds:", error);
  }
  kinds = {
    composite: new Set((composite || []).map((c) => c.name)),
    embedding: new Set((embedding || []).map((c) => c.name)),
  };
  return kinds;
}

export function isComposite(name) {
  return Boolean(kinds?.composite?.has(name));
}

export function isEmbedding(name) {
  return Boolean(kinds?.embedding?.has(name));
}

// Category grouping is not retriever-specific: the generic component tree owns
// it, and the retriever pickers keep using it under their historical names.
export {
  componentCategory as retrieverCategory,
  sortByCategory,
} from "../../../components/shared/componentTree/componentTreeUtils";
