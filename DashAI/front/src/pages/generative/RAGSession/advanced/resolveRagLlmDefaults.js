import { getComponents } from "../../../../api/component";
import { resolveDefaults } from "../../../../utils/schema";

/**
 * The only LLM parameters RAG overrides for its helper stages.
 *
 * Kept in sync with `rag_llm_param_overrides()` in
 * `DashAI/back/models/RAG/RAG_defaults.py`. The owning component's placeholder
 * also carries the rest of the default LLM recipe (`device`,
 * `frequency_penalty`, ...), which must not be seeded over the selected
 * model's own values.
 */
const RAG_LLM_OVERRIDE_KEYS = ["temperature", "context_window", "max_tokens"];

/**
 * Resolve the seed values for a RAG stage's nested LLM.
 *
 * `resolveDefaults` builds a nested component's defaults from the LLM's own
 * schema alone, so it reports that model's generic placeholders -- a 512-token
 * context window, a 0.7 temperature, a 100-token budget. RAG deliberately runs
 * its helper LLMs on a different budget and states it in the *owning* field's
 * placeholder (`llm_model.placeholder.params`).
 *
 * The shared formatter cannot see those params, so a form seeded with the
 * generic values would both display the wrong budget and persist it on the
 * next edit, overriding what the backend resolves for an empty reference.
 * This RAG-local step restores that intent without changing the shared
 * formatter: only `RAG_LLM_OVERRIDE_KEYS` are copied from the owner
 * placeholder, so model-specific values such as `device` keep their own
 * defaults.
 *
 * @param {string} ownerComponent - Registered name of the stage component that
 *   declares the `llm_model` field (a transformer or a retriever).
 * @param {string} llmComponent - Registered name of the selected LLM.
 * @returns {Promise<object>} The LLM's schema defaults with the RAG-owned
 *   placeholder params applied on top.
 */
export async function resolveRagLlmDefaults(ownerComponent, llmComponent) {
  const defaults = await resolveDefaults(llmComponent);
  // Without an owner there is no schema declaring RAG overrides; the caller
  // then simply gets the LLM's own defaults, exactly as before.
  if (!ownerComponent) return defaults;

  try {
    const response = await getComponents({ model: ownerComponent });
    const owner = Array.isArray(response) ? response[0] : response;
    const placeholderParams =
      owner?.schema?.properties?.llm_model?.placeholder?.params ?? {};
    const overrides = {};
    for (const key of RAG_LLM_OVERRIDE_KEYS) {
      const ownerDeclaresKey = Object.prototype.hasOwnProperty.call(
        placeholderParams,
        key,
      );
      // Only seed a key the selected LLM actually declares; a model with a
      // differently named context window (DeepSeek's `n_ctx`) must not receive
      // a `context_window` it would silently ignore.
      const modelDeclaresKey = Object.prototype.hasOwnProperty.call(
        defaults,
        key,
      );
      if (ownerDeclaresKey && modelDeclaresKey) {
        overrides[key] = placeholderParams[key];
      }
    }
    return { ...defaults, ...overrides };
  } catch (error) {
    console.warn(
      `[resolveRagLlmDefaults] Failed to read the RAG overrides of ${ownerComponent}:`,
      error,
    );
    return defaults;
  }
}
