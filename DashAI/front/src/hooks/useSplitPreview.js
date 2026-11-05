import { useCallback, useEffect, useState } from "react";
import { previewSplit } from "../api/splitter";
import { getApiErrorMessage } from "../utils/apiError";

// Wait for the form to settle before asking: every keystroke would be a
// request otherwise.
export const SPLIT_PREVIEW_DEBOUNCE_MS = 250;
// A backend that does not answer would leave the step drawing forever.
export const SPLIT_PREVIEW_TIMEOUT_MS = 20000;

/**
 * The preview of a split, as the splitter computes it on the dataset.
 *
 * The answer belongs to the request it was made for: while a newer request is
 * pending, no preview is returned, so a screen never takes an old answer for
 * the current configuration. A superseded request is aborted, and one that
 * does not answer in time fails.
 *
 * @param {object} request
 * @param {number} request.datasetId the dataset being split
 * @param {string|null} request.splitterName null when no splitter is chosen
 * @param {object} request.params the splitter's parameters
 * @param {string|null} request.splitType how a holdout is given, if it is one
 * @param {object|null} request.indexes row indexes typed by hand
 * @returns {{preview: object|null, loading: boolean, error: string|null,
 *   errorStatus: number|null, retry: function}} `error` is the backend's
 *   reason for a failed request, `errorStatus` its HTTP status (null when no
 *   answer came), and `retry` asks again.
 */
export default function useSplitPreview({
  datasetId,
  splitterName,
  params,
  splitType = null,
  indexes = null,
}) {
  const [attempt, setAttempt] = useState(0);
  const requestKey = splitterName
    ? JSON.stringify({
        datasetId,
        splitterName,
        params,
        splitType,
        indexes,
        attempt,
      })
    : null;
  const [answer, setAnswer] = useState({
    key: null,
    preview: null,
    error: null,
    errorStatus: null,
  });

  useEffect(() => {
    if (!requestKey) return undefined;
    let cancelled = false;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const preview = await previewSplit(
          { datasetId, splitterName, params, splitType, indexes },
          { signal: controller.signal, timeout: SPLIT_PREVIEW_TIMEOUT_MS },
        );
        if (!cancelled) {
          setAnswer({
            key: requestKey,
            preview,
            error: null,
            errorStatus: null,
          });
        }
      } catch (error) {
        if (!cancelled) {
          setAnswer({
            key: requestKey,
            preview: null,
            error: getApiErrorMessage(error) || null,
            errorStatus: error?.response?.status ?? null,
          });
        }
      }
    }, SPLIT_PREVIEW_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      controller.abort();
    };
    // The key stands for every value the request is made of.
  }, [requestKey]);

  const retry = useCallback(() => setAttempt((count) => count + 1), []);

  const current = requestKey !== null && answer.key === requestKey;
  return {
    preview: current ? answer.preview : null,
    loading: requestKey !== null && !current,
    error: current ? answer.error : null,
    errorStatus: current ? answer.errorStatus : null,
    retry,
  };
}
