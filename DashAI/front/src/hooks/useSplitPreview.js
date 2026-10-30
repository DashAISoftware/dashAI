import { useEffect, useState } from "react";
import { previewSplit } from "../api/splitter";

// Wait for the form to settle before asking: every keystroke would be a
// request otherwise.
export const SPLIT_PREVIEW_DEBOUNCE_MS = 250;

/**
 * The preview of a split, as the splitter computes it on the dataset.
 *
 * The answer belongs to the request it was made for: while a newer request is
 * pending, no preview is returned, so a screen never takes an old answer for
 * the current configuration.
 *
 * @param {object} request
 * @param {number} request.datasetId the dataset being split
 * @param {string|null} request.splitterName null when no splitter is chosen
 * @param {object} request.params the splitter's parameters
 * @param {string|null} request.splitType how a holdout is given, if it is one
 * @param {object|null} request.indexes row indexes typed by hand
 * @returns {{preview: object|null, loading: boolean, error: string|null}}
 */
export default function useSplitPreview({
  datasetId,
  splitterName,
  params,
  splitType = null,
  indexes = null,
}) {
  const requestKey = splitterName
    ? JSON.stringify({ datasetId, splitterName, params, splitType, indexes })
    : null;
  const [answer, setAnswer] = useState({
    key: null,
    preview: null,
    error: null,
  });

  useEffect(() => {
    if (!requestKey) return undefined;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const preview = await previewSplit({
          datasetId,
          splitterName,
          params,
          splitType,
          indexes,
        });
        if (!cancelled) setAnswer({ key: requestKey, preview, error: null });
      } catch (error) {
        if (!cancelled) {
          setAnswer({
            key: requestKey,
            preview: null,
            error: error?.response?.data?.detail ?? error?.message ?? null,
          });
        }
      }
    }, SPLIT_PREVIEW_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // The key stands for every value the request is made of.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey]);

  const current = requestKey !== null && answer.key === requestKey;
  return {
    preview: current ? answer.preview : null,
    loading: requestKey !== null && !current,
    error: current ? answer.error : null,
  };
}
