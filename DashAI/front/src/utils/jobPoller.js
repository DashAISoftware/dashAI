import api from "../api/api";

import { getJobChanges, isQueueEmpty } from "../api/job";

const POLLER_INSTANCE_ID = Math.random().toString(36).slice(2, 10);

const LS_KEY = "active_job_poller";
const BEAT_KEY = "active_job_poller_beat";
const BEAT_MS = 1500;
const STALE_MS = 6000;

export const state = {
  started: false,
  inFlight: false,
  timerId: null,
  since: "1970-01-01 00:00:00.000000",
  subs: new Set(),
  intervalMs: 3000,
  confirmDelayMs: 2000,
  mode: "sleep",
  singletonHeld: false,
  heartbeatId: null,

  triggerStatuses: ["started", "finished", "error"],

  noChangeWhileNotEmptyStreak: 0,
  coastIntervalMs: 2000,
  maxNoChangeStreakBeforeSleep: 2,
};

function startHeartbeat() {
  try {
    localStorage.setItem(BEAT_KEY, String(Date.now()));
  } catch {}
  state.heartbeatId = setInterval(() => {
    try {
      localStorage.setItem(BEAT_KEY, String(Date.now()));
    } catch {}
  }, BEAT_MS);
}

function stopHeartbeat() {
  if (state.heartbeatId) {
    clearInterval(state.heartbeatId);
    state.heartbeatId = null;
  }
}

function holdSingleton() {
  try {
    const current = localStorage.getItem(LS_KEY);
    const lastBeat = Number(localStorage.getItem(BEAT_KEY) || 0);
    const fresh = Date.now() - lastBeat < STALE_MS;

    if (current && current !== POLLER_INSTANCE_ID && fresh) {
      console.warn(
        `[JobPoller ${POLLER_INSTANCE_ID}] another poller active: ${current}`,
      );
      return false;
    }

    localStorage.setItem(LS_KEY, POLLER_INSTANCE_ID);
    window.addEventListener("beforeunload", releaseSingleton);
    state.singletonHeld = true;
    startHeartbeat();
    return true;
  } catch {
    state.singletonHeld = true;
    startHeartbeat();
    return true;
  }
}

function releaseSingleton() {
  try {
    if (localStorage.getItem(LS_KEY) === POLLER_INSTANCE_ID) {
      localStorage.removeItem(LS_KEY);
      localStorage.removeItem(BEAT_KEY);
    }
  } catch {}
  state.singletonHeld = false;
  stopHeartbeat();
}

function clearTimer() {
  if (state.timerId) {
    clearTimeout(state.timerId);
    state.timerId = null;
  }
}

function schedule(nextMs) {
  clearTimer();
  state.timerId = setTimeout(pollOnce, Math.max(0, nextMs));
}

function notify(jobs, meta) {
  for (const cb of Array.from(state.subs)) {
    try {
      cb(jobs, meta);
    } catch (e) {
      console.error("[JobPoller] subscriber error", e);
    }
  }
}

async function pollOnce() {
  if (!state.started || state.inFlight) return;
  state.inFlight = true;

  try {
    const data = await getJobChanges(state.since);
    const jobs = data.jobs || [];
    const cursor = data.cursor || state.since;
    const queueEmpty = !!data.queue_empty;
    const recentlyCompleted = !!data.recently_completed;
    const serverNow = data.server_now || cursor;

    state.since = cursor;

    notify(jobs, { cursor, queueEmpty, recentlyCompleted, serverNow });

    const changed = jobs.length > 0;

    if (changed) {
      state.noChangeWhileNotEmptyStreak = 0;
    }

    if (queueEmpty && !changed && !recentlyCompleted) {
      if (state.mode !== "confirm") {
        state.mode = "confirm";
        schedule(state.confirmDelayMs);
        return;
      }
      state.mode = "sleep";
      clearTimer();
      return;
    }

    if (queueEmpty && !changed && recentlyCompleted) {
      state.mode = "confirm";
      schedule(state.confirmDelayMs);
      return;
    }

    if (!queueEmpty && changed) {
      state.mode = "active";
      schedule(state.intervalMs);
      return;
    }

    if (!queueEmpty && !changed) {
      state.noChangeWhileNotEmptyStreak += 1;

      if (
        state.noChangeWhileNotEmptyStreak >= state.maxNoChangeStreakBeforeSleep
      ) {
        state.mode = "sleep";
        clearTimer();
      } else if (state.noChangeWhileNotEmptyStreak === 1) {
        state.mode = "active";
        schedule(state.intervalMs);
      } else {
        state.mode = "coast";
        schedule(state.coastIntervalMs);
      }
      return;
    }

    state.mode = "active";
    schedule(state.intervalMs);
  } catch (e) {
    console.error("[JobPoller] poll error:", e?.message || e);
    schedule(Math.max(2000, state.intervalMs));
  } finally {
    state.inFlight = false;
  }
}

export function startJobPoller(intervalMs = 3000) {
  state.intervalMs = intervalMs;
  if (state.started) return true;
  if (!holdSingleton()) return false;

  state.started = true;
  state.mode = "active";
  state.noChangeWhileNotEmptyStreak = 0;
  schedule(0);
  return true;
}

export function stopJobPoller() {
  clearTimer();
  state.started = false;
  state.mode = "sleep";
  releaseSingleton();
}

export function subscribeJobs(cb) {
  state.subs.add(cb);
  return () => {
    state.subs.delete(cb);
  };
}

export function resetSince() {
  state.since = "1970-01-01 00:00:00.000000";
}

export function setConfirmDelay(ms) {
  state.confirmDelayMs = Math.max(0, Number(ms) || 0);
}

export function setTriggerStatuses(statuses) {
  try {
    const arr = Array.isArray(statuses) ? statuses : [];
    state.triggerStatuses = arr;
  } catch {
    state.triggerStatuses = ["started", "finished", "error"];
  }
}

/**
 * Wake the poller if a new job was enqueued.
 * Safe to call after enqueue events to wake the poller.
 */
export async function checkQueueAndMaybeStartPolling() {
  try {
    const isEmpty = await isQueueEmpty();
    if (!isEmpty) {
      if (!state.started) startJobPoller(state.intervalMs);
      else if (state.mode === "sleep") schedule(0);
      return true;
    }
    return false;
  } catch (e) {
    console.warn("[JobPoller] is_empty check failed:", e?.message || e);
    if (!state.started) startJobPoller(state.intervalMs);
    return true;
  }
}

/**
 * Manual refresh (UI buttons). Does not reset cursor.
 */
export async function forceRefreshNow() {
  if (!state.started) {
    startJobPoller(state.intervalMs);
    return;
  }

  schedule(0);

  try {
    const r = await api.get("/v1/job/is_empty");
    const isEmpty = !!r?.data?.is_empty;
    if (!isEmpty && state.mode === "sleep") {
      setTimeout(() => schedule(0), 500);
    }
  } catch (e) {
    console.warn("[JobPoller] is_empty check failed:", e?.message || e);
  }
}
