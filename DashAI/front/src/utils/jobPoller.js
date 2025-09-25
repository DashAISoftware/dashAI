import { getJobs, getJobStatus, isQueueEmpty, getJobChanges } from "../api/job";

const POLL_INTERVAL = 1000; // Default polling interval (2 seconds)

// Central state
const state = {
  active: false, // Is polling currently active
  intervalId: null, // ID of the main polling interval
  subscribers: new Set(), // Components listening for job updates
  jobWatchers: new Map(), // Map of individual jobs being tracked (jobId -> {intervalId, onSuccess, onError})
  lastFetchTime: null, // Last successful fetch time
  lastCursor: null, // Last cursor for job changes
  lastCompletionTime: null, // Last time a job was completed
};

/**
 * Start the global job polling system
 */
export function startJobPoller() {
  if (state.active) return;

  console.log("[JobPoller] Starting global polling");
  state.active = true;

  // Clear any existing interval
  if (state.intervalId) {
    clearInterval(state.intervalId);
  }

  // Poll immediately and then at regular intervals
  pollJobs();
  state.intervalId = setInterval(pollJobs, POLL_INTERVAL);
}

/**
 * Stop the global job polling system
 */
export function stopJobPoller() {
  if (!state.active) return;

  console.log("[JobPoller] Stopping global polling");
  if (state.intervalId) {
    clearInterval(state.intervalId);
    state.intervalId = null;
  }
  state.active = false;
}

/**
 * Check if there are any active jobs in the list
 */
function hasActiveJobs(jobs) {
  return jobs.some(
    (job) => job.status === "not_started" || job.status === "started",
  );
}

/**
 * Main polling function that checks all jobs
 */
async function pollJobs() {
  try {
    console.log(
      "[JobPoller] Polling jobs, subscribers:",
      state.subscribers.size,
      "watchers:",
      state.jobWatchers.size,
    );

    // Si no hay suscriptores ni watchers, verificar si podemos detener el polling
    if (state.subscribers.size === 0 && state.jobWatchers.size === 0) {
      const isEmpty = await isQueueEmpty();
      console.log("[JobPoller] Queue empty?", isEmpty);
      if (isEmpty) {
        console.log(
          "[JobPoller] No subscribers, no watchers, and queue is empty - stopping",
        );
        stopJobPoller();
        return;
      }
    }

    // Obtener cambios en los jobs desde el último cursor
    const changeData = await getJobChanges(state.lastCursor);
    state.lastCursor = changeData.cursor;
    state.lastFetchTime = new Date();

    // Usar all_jobs que ya viene en la respuesta
    const jobsToProcess = changeData.all_jobs || [];

    console.log(
      "ALL JOBS:",
      jobsToProcess.map((j) => ({ id: j.id, status: j.status })),
      "Recently completed:",
      changeData.recently_completed,
    );

    // Verificar si hay jobs activos
    const activeJobsExist = hasActiveJobs(jobsToProcess);
    console.log("[JobPoller] Active jobs exist?", activeJobsExist);

    // Notificar a los suscriptores globales
    for (const subscriber of state.subscribers) {
      try {
        subscriber(jobsToProcess);
      } catch (error) {
        console.error("[JobPoller] Subscriber error:", error);
      }
    }

    // Verificar jobs específicos que se están siguiendo
    for (const [jobId, watcher] of state.jobWatchers.entries()) {
      // Buscar el job en la lista
      console.log(`Looking for job with ID: ${jobId}`);
      const job = jobsToProcess.find((j) => j.id === jobId);
      console.log(`Found job? ${!!job}, status: ${job?.status}`);

      if (job) {
        if (job.status === "finished") {
          if (watcher.onSuccess) watcher.onSuccess(job);
          stopJobPolling(jobId);
        } else if (job.status === "error") {
          if (watcher.onError) watcher.onError(job);
          stopJobPolling(jobId);
        }
      }
    }

    // Verificar si hay completados recientemente
    if (changeData.recently_completed) {
      state.lastCompletionTime = Date.now();
      console.log(
        "[JobPoller] Recently completed jobs detected, keeping polling active",
      );
    }

    // Calcular tiempo desde la última completación
    const MIN_POLLING_AFTER_COMPLETION = 5000; // 5 segundos
    const timePassedSinceCompletion = state.lastCompletionTime
      ? Date.now() - state.lastCompletionTime
      : Infinity;

    // Decidir si detener el polling
    if (
      !activeJobsExist &&
      state.jobWatchers.size === 0 &&
      !changeData.recently_completed &&
      timePassedSinceCompletion > MIN_POLLING_AFTER_COMPLETION
    ) {
      console.log(
        "[JobPoller] No active jobs, no watchers, nothing recently completed - stopping polling",
      );
      stopJobPoller();
      return;
    }
  } catch (error) {
    console.error("[JobPoller] Error polling jobs:", error);
  }
}

/**
 * Start polling for a specific job
 * @param {string} jobId - ID of the job to watch
 * @param {Function} onSuccess - Callback when job completes successfully
 * @param {Function} onError - Callback when job fails
 */
export function startJobPolling(jobId, onSuccess, onError) {
  if (!jobId) return;

  console.log(`[JobPoller] Starting to watch job: ${jobId}`);

  // Stop existing polling for this job if any
  stopJobPolling(jobId);

  // Create a dedicated interval for this job
  const intervalId = setInterval(async () => {
    try {
      const jobDetails = await getJobStatus(jobId);
      console.log(`[JobPoller] Job ${jobId} status:`, jobDetails.status);

      if (jobDetails.status === "finished") {
        if (typeof onSuccess === "function") onSuccess(jobDetails);
        stopJobPolling(jobId);
      } else if (jobDetails.status === "error") {
        if (typeof onError === "function") onError(jobDetails);
        stopJobPolling(jobId);
      }
    } catch (error) {
      console.error(`[JobPoller] Error checking job ${jobId}:`, error);
    }
  }, POLL_INTERVAL);

  // Store the watcher
  state.jobWatchers.set(jobId, {
    intervalId,
    onSuccess,
    onError,
  });

  // Make sure global polling is active
  if (!state.active) {
    startJobPoller();
  }
}

/**
 * Stop polling for a specific job
 */
export function stopJobPolling(jobId) {
  if (!state.jobWatchers.has(jobId)) return;

  const watcher = state.jobWatchers.get(jobId);
  if (watcher.intervalId) {
    clearInterval(watcher.intervalId);
  }

  state.jobWatchers.delete(jobId);
  console.log(`[JobPoller] Stopped polling for job: ${jobId}`);
}

/**
 * Subscribe to updates for all jobs
 */
export function subscribeJobs(callback) {
  if (typeof callback !== "function") return () => {};

  state.subscribers.add(callback);

  // Make sure polling is active
  if (!state.active) {
    startJobPoller();
  }

  return () => {
    state.subscribers.delete(callback);

    // If no more subscribers and no job watchers, stop polling
    if (state.subscribers.size === 0 && state.jobWatchers.size === 0) {
      stopJobPoller();
    }
  };
}

/**
 * Force an immediate refresh of job status
 */
export function forceRefreshNow() {
  if (!state.active) {
    startJobPoller();
  } else {
    pollJobs();
  }
}

/**
 * Check if the queue has jobs and start polling if needed
 */
export async function checkQueueAndMaybeStartPolling() {
  try {
    const isEmpty = await isQueueEmpty();

    if (!isEmpty) {
      // Check if there are active jobs before starting polling
      const jobs = await getJobs();
      const activeJobsExist = hasActiveJobs(jobs);

      console.log(
        "[JobPoller] Queue empty?",
        isEmpty,
        "Active jobs?",
        activeJobsExist,
      );

      if (activeJobsExist && !state.active) {
        startJobPoller();
      }

      return activeJobsExist;
    }
    return false;
  } catch (error) {
    console.error("[JobPoller] Error checking queue:", error);
    return false;
  }
}

/**
 * Clean up all resources (call on app shutdown or navigation)
 */
export function cleanupJobPoller() {
  // Clear main interval
  if (state.intervalId) {
    clearInterval(state.intervalId);
    state.intervalId = null;
  }

  // Clear all job watcher intervals
  for (const [jobId, watcher] of state.jobWatchers.entries()) {
    if (watcher.intervalId) {
      clearInterval(watcher.intervalId);
    }
  }

  // Reset state
  state.active = false;
  state.jobWatchers.clear();
  state.subscribers.clear();
  state.lastFetchTime = null;
}
