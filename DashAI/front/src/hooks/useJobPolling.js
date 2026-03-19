import { useEffect, useRef, useState, useCallback } from "react";
import { getJobs } from "../api/job";
import {
  subscribeJobs,
  forceRefreshNow as _forceRefreshNow,
  checkQueueAndMaybeStartPolling as _checkQueueAndMaybeStartPolling,
  startJobPolling as _startJobPolling,
  stopJobPolling as _stopJobPolling,
} from "../utils/jobPoller";

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

export function useJobManager() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getJobs()
      .then((data) => {
        if (Array.isArray(data)) {
          setJobs(data);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error loading jobs:", err);
        setError("Failed to load jobs");
        setLoading(false);
      });

    const unsubscribe = subscribeJobs((updatedJobs) => {
      if (Array.isArray(updatedJobs)) {
        setJobs(updatedJobs);
        setLoading(false);
      }
    });

    return unsubscribe;
  }, []);

  const refresh = useCallback(() => {
    setLoading(true);
    forceRefreshNow();
  }, []);

  return { jobs, loading, error, refresh };
}

export const forceRefreshNow = _forceRefreshNow;
export const checkQueueAndMaybeStartPolling = _checkQueueAndMaybeStartPolling;
export const startJobPolling = _startJobPolling;
export const stopJobPolling = _stopJobPolling;
