import { useEffect, useState } from "react";
import { getComponents } from "../api/component";
import { sessionColumns } from "../components/models/modelSession/columnRoles";

/**
 * What each task declares about itself, fetched once per task name.
 *
 * Several screens read a session's columns, and only the task can say which
 * of its roles are the model's inputs and which its outputs, so every one of
 * them asks for the same metadata. The request is shared.
 */
const metadataCache = new Map();

/**
 * Fetch a task's metadata, sharing one request per task name.
 *
 * @param {string} taskName a session's task_name
 * @returns {Promise<object>} the task metadata ({} when it cannot be read)
 */
export function fetchTaskMetadata(taskName) {
  if (!metadataCache.has(taskName)) {
    const request = getComponents({ model: taskName })
      .then((component) => component?.metadata ?? {})
      .catch((error) => {
        console.error(`Error fetching the ${taskName} metadata`, error);
        metadataCache.delete(taskName);
        return {};
      });
    metadataCache.set(taskName, request);
  }
  return metadataCache.get(taskName);
}

/**
 * Read the metadata a task declares.
 *
 * @param {string|null} taskName a session's task_name
 * @returns {object|null} the task metadata, or null while it is unknown
 */
export function useTaskMetadata(taskName) {
  const [metadata, setMetadata] = useState(null);

  useEffect(() => {
    if (!taskName) {
      setMetadata(null);
      return undefined;
    }
    let cancelled = false;
    fetchTaskMetadata(taskName).then((value) => {
      if (!cancelled) setMetadata(value);
    });
    return () => {
      cancelled = true;
    };
  }, [taskName]);

  return metadata;
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
