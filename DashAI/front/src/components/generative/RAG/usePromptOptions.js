import { useEffect, useState } from "react";
import { getComponents } from "../../../api/component";

/**
 * Load the prompt components registered under a prompt parent.
 *
 * The whole list is returned and callers filter it while rendering, so a prompt
 * that a technique filter rejects can still be shown as the current value.
 * Options are fetched once per parent, and a response that arrives after the
 * parent changed, or after unmount, is ignored.
 *
 * @param {string} parent - The prompt parent class to list children of.
 * @returns {{options: object[], loading: boolean, error: boolean}} Every
 *   loaded option, whether a request is in flight, and whether the last one
 *   failed.
 */
export default function usePromptOptions(parent) {
  const [loaded, setLoaded] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    // A card must never show the previous parent's prompts while the new ones
    // are on their way.
    setLoaded([]);
    setError(false);

    if (!parent) {
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);

    getComponents({ componentParent: parent })
      .then((components) => {
        if (cancelled) return;
        setLoaded(
          (components ?? []).filter(
            (component) => component.configurable_object !== false,
          ),
        );
      })
      .catch((loadFailure) => {
        if (cancelled) return;
        console.error(`Failed to load prompts under ${parent}:`, loadFailure);
        setLoaded([]);
        setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [parent]);

  return { options: loaded, loading, error };
}
