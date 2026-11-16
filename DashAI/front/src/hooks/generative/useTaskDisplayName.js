import { useGenerative } from "../../components/generative/GenerativeContext";

/**
 * The friendly, localized name of a generative task or workflow.
 *
 * Names come from the backend already translated, so a view scoped to one
 * workflow can label itself without carrying a string of its own. Falls back
 * to the given name while the lists are still loading.
 *
 * @param {string} taskName - A task or workflow registry name (e.g. "RAGWorkflow").
 * @returns {string} Its display name, or the given name as a fallback.
 */
export function useTaskDisplayName(taskName) {
  const { tasks, workflows } = useGenerative() ?? {};
  const component = [...(tasks ?? []), ...(workflows ?? [])].find(
    (candidate) => candidate.name === taskName,
  );
  return component?.display_name || taskName;
}
