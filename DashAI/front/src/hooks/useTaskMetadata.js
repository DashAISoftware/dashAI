import { useEffect, useState } from "react";
import { getComponents } from "../api/component";
import { sessionColumns } from "../components/models/modelSession/columnRoles";
import { getApiDetail } from "../utils/apiError";

/**
 * What each task declares about itself, fetched once per task name.
 *
 * Several screens read a session's columns, and only the task can say which
 * of its roles are the model's inputs and which its outputs, so every one of
 * them asks for the same metadata. The request is shared.
 */
const metadataCache = new Map();

/**
 * A task whose metadata cannot be read, typically because it is not
 * registered (a plugin that was uninstalled). A session of it cannot say
 * which of its columns are the model's inputs, so a caller that needs them
 * should say so rather than show nothing.
 */
export class TaskMetadataError extends Error {
  constructor(taskName, detail) {
    super(detail || `The metadata of ${taskName} cannot be read.`);
    this.name = "TaskMetadataError";
    this.taskName = taskName;
    this.detail = detail;
  }
}

/**
 * Fetch a task's metadata, sharing one request per task name.
 *
 * A failed request is not kept, so the next call asks again.
 *
 * @param {string} taskName a session's task_name
 * @returns {Promise<object>} the task metadata
 * @throws {TaskMetadataError} when it cannot be read, with the backend's reason
 */
export function fetchTaskMetadata(taskName) {
  if (!metadataCache.has(taskName)) {
    const request = getComponents({ model: taskName })
      .then((component) => component?.metadata ?? {})
      .catch((error) => {
        console.error(`Error fetching the ${taskName} metadata`, error);
        metadataCache.delete(taskName);
        throw new TaskMetadataError(taskName, getApiDetail(error));
      });
    metadataCache.set(taskName, request);
  }
  return metadataCache.get(taskName);
}

/**
 * Read the metadata a task declares.
 *
 * What it holds is kept with the task it belongs to, so when `taskName`
 * changes the previous task's metadata is never returned, not even for the
 * render before the new one arrives.
 *
 * @param {string|null} taskName a session's task_name
 * @returns {object|null} the task metadata ({} when it cannot be read), or
 *   null while it is unknown
 */
export function useTaskMetadata(taskName) {
  const [loaded, setLoaded] = useState({ taskName: null, metadata: null });

  useEffect(() => {
    if (!taskName) return undefined;
    let cancelled = false;
    fetchTaskMetadata(taskName)
      .catch(() => ({}))
      .then((metadata) => {
        if (!cancelled) setLoaded({ taskName, metadata });
      });
    return () => {
      cancelled = true;
    };
  }, [taskName]);

  return taskName && loaded.taskName === taskName ? loaded.metadata : null;
}

/**
 * A session's columns as the model's inputs and outputs (see sessionColumns).
 *
 * @param {object|null} session a model session as the API returns it
 * @returns {object|null} `{inputs, inputRefs, outputs, target}`, or null
 *   while the session or its task's metadata is not known yet
 */
export function useSessionColumns(session) {
  const metadata = useTaskMetadata(session?.task_name);
  if (!session || !metadata) return null;
  return sessionColumns(session, metadata);
}
