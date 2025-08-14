// src/hooks/useJobPolling.js
import { useEffect, useRef } from "react";
import {
  startJobPoller,
  stopJobPoller,
  subscribeJobs,
  setConfirmDelay,
  setTriggerStatuses,
  resetSince as resetPollerSince,
  state as pollerState,
  checkQueueAndMaybeStartPolling as _checkQueueAndMaybeStartPolling,
  forceRefreshNow as _forceRefreshNow,
} from "../utils/jobPoller";

/**
 * Hook to consume the central poller.
 * - Starts poller if not running
 * - Subscribes the provided callback
 * - Stops poller when last subscriber unsubscribes
 *
 * onJobsChanged: (changesArray, meta) => void
 * meta: { cursor, queueEmpty, recentlyCompleted, serverNow }
 */
export default function useJobPolling(
  interval = 3000,
  onJobsChanged,
  triggerStatuses = ["started", "finished", "error"],
  confirmDelayMs = 2000,
) {
  const savedCbRef = useRef(onJobsChanged);
  savedCbRef.current = onJobsChanged;

  useEffect(() => {
    setConfirmDelay(confirmDelayMs);
    setTriggerStatuses(triggerStatuses);

    if (!pollerState.started) {
      startJobPoller(interval);
    }

    const unsub = subscribeJobs((changes, meta) => {
      if (typeof savedCbRef.current === "function") {
        savedCbRef.current(changes, meta);
      }
    });

    return () => {
      unsub();
      if (pollerState.subs.size === 0) {
        stopJobPoller();
      }
    };
  }, [interval, confirmDelayMs, JSON.stringify(triggerStatuses)]);
}

export { resetPollerSince as resetSince };
export const checkQueueAndMaybeStartPolling = _checkQueueAndMaybeStartPolling;
export const forceRefreshNow = _forceRefreshNow;
