import { getModelSessionById } from "../api/modelSession";

/**
 * The data file path a session's step-2/step-3 UI should read from right
 * now: the current preprocessed reference partition if one exists, else
 * the raw dataset. Mirrors the backend's own logic in
 * `GET /model-session/{id}/preprocessed-columns`.
 *
 * Raw-dataset case: `dataset.file_path` is the dataset's *root* storage
 * folder — every by-path dataset HTTP route (`/dataset/file/`,
 * `/dataset/filter/`, `/dataset/types/file`) appends its own `/dataset`
 * segment server-side before reading `data.arrow` (confirmed against
 * `DashAI/back/api/api_v1/endpoints/datasets.py` and `model_sessions.py`'s
 * own `f"{dataset.file_path}/dataset"` convention). Appending `/dataset`
 * here too double-nests it (`.../dataset/dataset/data.arrow`, a path that
 * doesn't exist) and 500s — pass the root straight through.
 */
export function getCurrentDataFilePath(session) {
  if (!session?.preprocessed_path) {
    return session?.dataset?.file_path;
  }
  const isCV =
    session.evaluation_strategy === "CrossValidationEvaluationStrategy";
  return isCV
    ? `${session.preprocessed_path}/full_dataset/train`
    : `${session.preprocessed_path}/train`;
}

const FINISHED = 3;
const ERROR = 4;

/**
 * Polls `GET /model-session/{id}` until `preprocessing_status` reaches a
 * terminal state. `preprocessing_huey_id` is populated (see
 * `update_session_converters`/`create_model_session`), but this stays a
 * dedicated interval rather than switching to the generic job-id-based
 * `jobPoller.js`: callers need the full refreshed session (columns,
 * preprocessed_path) on completion, not just a raw job status record.
 * Callers additionally register the huey id with `startJobPolling` purely
 * so the shared job-queue widget observes the job live. See
 * `FormSessionConverterSection.jsx` and `PreprocessingStep.jsx`.
 *
 * @returns {() => void} cancel function — call on unmount to stop polling.
 */
export function pollSessionPreprocessing(
  sessionId,
  { onFinished, onError, intervalMs = 1000 },
) {
  let cancelled = false;
  const tick = async () => {
    if (cancelled) return;
    try {
      const session = await getModelSessionById(sessionId);
      if (cancelled) return;
      if (session.preprocessing_status === FINISHED) {
        onFinished(session);
        return;
      }
      if (session.preprocessing_status === ERROR) {
        onError(session);
        return;
      }
      timeoutId = setTimeout(tick, intervalMs);
    } catch (error) {
      if (!cancelled) onError(null, error);
    }
  };
  let timeoutId = setTimeout(tick, intervalMs);
  return () => {
    cancelled = true;
    clearTimeout(timeoutId);
  };
}
