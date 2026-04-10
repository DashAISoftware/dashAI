import { useEffect, useRef, useState, useCallback } from "react";
import { getJobs } from "../api/job";
import {
  subscribeJobs,
  forceRefreshNow as _forceRefreshNow,
  checkQueueAndMaybeStartPolling as _checkQueueAndMaybeStartPolling,
  startJobPolling as _startJobPolling,
  stopJobPolling as _stopJobPolling,
} from "../utils/jobPoller";

function parseTimestamp(ts) {
  if (!ts) return new Date(0);
  return ts.includes("T") ? new Date(ts) : new Date(ts.replace(" ", "T") + "Z");
}

function mergeJobsById(previousJobs, changedJobs) {
  const byId = new Map(previousJobs.map((job) => [job.id, job]));

  changedJobs.forEach((job) => {
    const prev = byId.get(job.id) || {};
    byId.set(job.id, { ...prev, ...job });
  });

  return Array.from(byId.values()).sort(
    (a, b) => parseTimestamp(b.last_update) - parseTimestamp(a.last_update),
  );
}

/**
 * Hook to subscribe to all job updates
 * @param {function} callback - Function called with updated jobs
 */
export default function useJobPolling(callback) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    const unsubscribe = subscribeJobs((jobs) => {
      if (typeof callbackRef.current === "function") {
        callbackRef.current(jobs);
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);
}

/**
 * Hook to track a specific job with callbacks
 * @param {string} jobId - ID of the job to track
 * @param {function} onSuccess - Callback when job succeeds
 * @param {function} onError - Callback when job fails
 */
export function useJobTracker(jobId, onSuccess, onError) {
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);

  // Keep callbacks updated
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!jobId) return;

    _startJobPolling(
      jobId,
      (result) => {
        if (typeof onSuccessRef.current === "function") {
          onSuccessRef.current(result);
        }
      },
      (result) => {
        if (typeof onErrorRef.current === "function") {
          onErrorRef.current(result);
        }
      },
    );

    return () => {
      _stopJobPolling(jobId);
    };
  }, [jobId]);
}

export function useJobManager() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAllJobs = useCallback(() => {
    setLoading(true);
    getJobs()
      .then((data) => {
        if (Array.isArray(data)) {
          setJobs(
            [...data].sort(
              (a, b) =>
                parseTimestamp(b.last_update) - parseTimestamp(a.last_update),
            ),
          );
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error loading jobs:", err);
        setError("Failed to load jobs");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchAllJobs();

    const unsubscribe = subscribeJobs((updatedJobs) => {
      if (Array.isArray(updatedJobs)) {
        // `updatedJobs` is incremental (changes since cursor), so merge it.
        setJobs((previousJobs) => mergeJobsById(previousJobs, updatedJobs));
        setLoading(false);
      }
    });

    return unsubscribe;
  }, []);

  const refresh = useCallback(() => {
    fetchAllJobs();
  }, [fetchAllJobs]);

  return { jobs, loading, error, refresh };
}

export const forceRefreshNow = _forceRefreshNow;
export const checkQueueAndMaybeStartPolling = _checkQueueAndMaybeStartPolling;
export const startJobPolling = _startJobPolling;
export const stopJobPolling = _stopJobPolling;
