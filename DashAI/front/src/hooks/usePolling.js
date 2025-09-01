import { useState, useEffect, useRef } from "react";

/**
 * Simple hook to manage polling intervals
 *
 * @param {Function} pollingFunction Function to call on each polling interval
 * @param {Object} options Configuration options
 * @returns Polling control functions and state
 */
export function usePolling(pollingFunction, options = {}) {
  const {
    interval = 2000, // Polling interval in ms
    enabled = true, // Whether polling is initially enabled
    stopOnCondition = null, // Optional function that returns true when polling should stop
  } = options;

  const [isPolling, setIsPolling] = useState(enabled);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  // Start polling function
  const startPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    setIsPolling(true);
  };

  // Stop polling function
  const stopPolling = () => {
    setIsPolling(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // Run once immediately and then start interval
  const executeAndSchedule = async () => {
    if (!mountedRef.current || !isPolling) return;

    try {
      // Call the polling function
      const result = await pollingFunction();

      // Check stop condition if provided
      if (stopOnCondition && stopOnCondition(result)) {
        stopPolling();
      }
    } catch (error) {
      console.error("Error in polling function:", error);
    }

    // Schedule next call if still polling
    if (mountedRef.current && isPolling) {
      intervalRef.current = setTimeout(executeAndSchedule, interval);
    }
  };

  // Effect to handle polling based on isPolling state
  useEffect(() => {
    if (isPolling) {
      // Execute immediately
      executeAndSchedule();
    } else if (intervalRef.current) {
      clearTimeout(intervalRef.current);
    }

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearTimeout(intervalRef.current);
      }
    };
  }, [isPolling, interval]);

  // Manually trigger the polling function
  const refresh = async () => {
    return await pollingFunction();
  };

  return {
    isPolling,
    startPolling,
    stopPolling,
    refresh,
  };
}
