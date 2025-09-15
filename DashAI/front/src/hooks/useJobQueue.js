import { useState, useEffect, useCallback, useRef } from "react";
import { getJobs } from "../api/job";
import useJobPolling from "./useJobPolling";

export default function useJobQueue(pollingInterval = 3000) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const activeRequestRef = useRef(null);
  const jobsRef = useRef([]);
  jobsRef.current = jobs;

  function normalize(row) {
    if (!row || typeof row !== "object") return null;
    const id = row.id ?? row.job_id ?? null;
    if (id == null) return null;

    const prev = jobsRef.current.find((j) => j.id === id) || {};

    return {
      ...prev,
      ...row,
      id,
      status: row.status ?? prev.status ?? "not_started",
      task_type: row.task_type ?? prev.task_type ?? null,
      job_name: row.job_name ?? prev.job_name ?? null,
      last_update:
        row.last_update ??
        row.updated_at ??
        prev.last_update ??
        prev.updated_at ??
        null,
      error_msg: row.error_msg ?? prev.error_msg ?? null,
    };
  }

  const applyChanges = useCallback((changes) => {
    if (!Array.isArray(changes) || changes.length === 0) return;

    console.log("Applying changes:", changes);

    setJobs((prev) => {
      const byId = new Map(prev.map((j) => [j.id, j]));

      for (const c of changes) {
        const n = normalize(c);
        if (!n) continue;

        const old = byId.get(n.id);
        if (old) {
          const oldTs = Date.parse(old.last_update || "0") || 0;
          const newTs = Date.parse(n.last_update || "0") || 0;

          if (newTs >= oldTs || old.status !== n.status) {
            byId.set(n.id, { ...old, ...n });
          }
        } else {
          byId.set(n.id, n);
        }
      }

      const list = Array.from(byId.values());
      list.sort(
        (a, b) =>
          (Date.parse(b.last_update || "0") || 0) -
          (Date.parse(a.last_update || "0") || 0),
      );

      return list;
    });
  }, []);

  const fetchJobs = useCallback(async (force = false) => {
    try {
      if (activeRequestRef.current) {
        activeRequestRef.current.abort();
        activeRequestRef.current = null;
      }
      const controller = new AbortController();
      activeRequestRef.current = controller;

      await Promise.resolve();

      const data = await getJobs();
      console.log("Jobs fetched:", data);

      const jobArray = Array.isArray(data) ? data : [];

      setJobs(jobArray);
      setLoading(false);
      setError(null);
    } catch (e) {
    } finally {
      activeRequestRef.current = null;
    }
  }, []);

  useEffect(() => {
    fetchJobs(false);
    return () => {
      if (activeRequestRef.current) activeRequestRef.current.abort();
    };
  }, [fetchJobs]);

  useJobPolling(
    pollingInterval,
    (changes, meta) => {
      const hasChanges = Array.isArray(changes) && changes.length > 0;
      if (hasChanges) applyChanges(changes);

      const justCompleted = !!meta?.recentlyCompleted;
      const queueNotEmpty = meta?.queueEmpty === false;

      const hasActiveLocal = jobsRef.current.some(
        (j) => j?.status === "not_started" || j?.status === "started",
      );

      if (hasChanges || justCompleted || queueNotEmpty || hasActiveLocal) {
        setTimeout(() => fetchJobs(true), justCompleted ? 700 : 0);
      }
    },
    ["started", "finished", "error"],
    2000,
  );

  return { jobs, loading, error, refetch: () => fetchJobs(true) };
}
