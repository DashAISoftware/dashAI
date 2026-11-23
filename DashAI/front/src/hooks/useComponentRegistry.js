import { useEffect, useState } from "react";
import { getChildComponents } from "../api/component";
import { findChildrenField } from "../components/shared/componentTree/componentTreeUtils";

/**
 * Loads the components of a registry parent and of every parent that the
 * containers among them declare for their children, until no new parent
 * appears. A failed request rejects, so a partial registry is never used.
 *
 * @param {string} parent - The registry parent class of the tree's root.
 * @returns {Promise<{byName: Map<string, object>,
 *   optionsByParent: Object<string, object[]>}>} The components by name, and the
 *   components that inherit each loaded parent.
 */
async function loadComponents(parent) {
  const byName = new Map();
  const optionsByParent = {};
  const queue = [parent];
  while (queue.length) {
    const next = queue.shift();
    if (next in optionsByParent) continue;
    const list = await getChildComponents(next, true);
    if (!Array.isArray(list)) {
      throw new Error(`The components of ${next} did not arrive as a list.`);
    }
    optionsByParent[next] = list;
    for (const component of list) {
      byName.set(component.name, component);
      const field = findChildrenField(component.schema);
      if (field && !(field.parent in optionsByParent)) queue.push(field.parent);
    }
  }
  return { byName, optionsByParent };
}

/**
 * Reads the message of a failed request.
 * @param {object} error - The rejection raised by the request.
 * @returns {string} A renderable reason.
 */
function failureReason(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return error?.message ?? String(error);
}

/**
 * Loads the component registry a component tree is built from.
 *
 * @param {string} parent - The registry parent class of the tree's root.
 * @returns {{registry: ({byName: Map<string, object>,
 *   optionsByParent: Object<string, object[]>}|null), error: (string|null)}}
 *   The registry once loaded, or the reason it could not be.
 */
export default function useComponentRegistry(parent) {
  const [state, setState] = useState({ registry: null, error: null });

  useEffect(() => {
    let cancelled = false;
    setState({ registry: null, error: null });
    loadComponents(parent)
      .then((registry) => {
        if (!cancelled) setState({ registry, error: null });
      })
      .catch((error) => {
        if (!cancelled)
          setState({ registry: null, error: failureReason(error) });
      });
    return () => {
      cancelled = true;
    };
  }, [parent]);

  return state;
}
