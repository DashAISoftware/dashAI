import { useEffect, useState } from "react";
import {
  getGeneratorComponents,
  getQueryTransformationComponents,
  getQueryTransformationPrompts,
} from "../api/rag";

/**
 * The message of a failed option request, preferring the API's detail.
 * @param {object} error - The rejection raised by the request.
 * @returns {string} A renderable reason.
 */
function loadFailureReason(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return error?.message ?? String(error);
}

/**
 * Requires an option request to answer with a list.
 * @param {*} data - The API answer.
 * @param {string} what - What was requested, for the error message.
 * @returns {Array} The list.
 * @throws {Error} When the answer is not a list.
 */
function requireList(data, what) {
  if (!Array.isArray(data)) {
    throw new Error(`The ${what} did not arrive as a list.`);
  }
  return data;
}

/**
 * Loads what the query transformation stage is configured from: the
 * transformer components, their prompts and the generation models.
 *
 * @returns {{transformers: Array, prompts: Array, generators: Array,
 *   loading: boolean, loadError: (string|null)}} The options, whether any is
 *   still loading, and the first failure reason.
 */
export default function useQueryTransformationOptions() {
  const [transformers, setTransformers] = useState([]);
  const [generators, setGenerators] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [loadingTransformers, setLoadingTransformers] = useState(true);
  const [loadingPrompts, setLoadingPrompts] = useState(true);
  const [loadingGenerators, setLoadingGenerators] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    const recordFailure = (error) =>
      setLoadError((previous) => previous ?? loadFailureReason(error));

    getQueryTransformationComponents()
      .then((data) => setTransformers(requireList(data, "query transformers")))
      .catch((error) => {
        console.error("Failed to load query transformers:", error);
        recordFailure(error);
      })
      .finally(() => setLoadingTransformers(false));
    getQueryTransformationPrompts()
      .then((data) =>
        setPrompts(requireList(data, "query transformation prompts")),
      )
      .catch((error) => {
        console.error("Failed to load query transformation prompts:", error);
        recordFailure(error);
      })
      .finally(() => setLoadingPrompts(false));
    getGeneratorComponents()
      .then((data) => setGenerators(requireList(data, "generation models")))
      .catch((error) => {
        console.error("Failed to load generation models:", error);
        recordFailure(error);
      })
      .finally(() => setLoadingGenerators(false));
  }, []);

  return {
    transformers,
    prompts,
    generators,
    loading: loadingTransformers || loadingPrompts || loadingGenerators,
    loadError,
  };
}
