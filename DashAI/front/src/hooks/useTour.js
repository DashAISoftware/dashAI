import { useState, useCallback, useEffect } from "react";

const TOUR_STORAGE_KEY = "dashai_tours_completed";

export const useTour = (tourKey) => {
  const [run, setRun] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const completedTours = JSON.parse(
      localStorage.getItem(TOUR_STORAGE_KEY) || "{}",
    );

    if (!completedTours[tourKey]) {
      const timer = setTimeout(() => setRun(true), 500);
      return () => clearTimeout(timer);
    }
  }, [tourKey]);

  const startTour = useCallback(() => {
    setStepIndex(0);
    setRun(true);
  }, []);

  const stopTour = useCallback(() => {
    setRun(false);
  }, []);

  const resetTour = useCallback(() => {
    setStepIndex(0);
    setRun(false);
  }, []);

  const goToStep = useCallback((step) => {
    setStepIndex(step);
  }, []);

  const nextStep = useCallback(() => {
    setStepIndex((prevIndex) => {
      return prevIndex + 1;
    });
  }, [stepIndex]);

  const markTourAsCompleted = useCallback(() => {
    const completedTours = JSON.parse(
      localStorage.getItem(TOUR_STORAGE_KEY) || "{}",
    );
    completedTours[tourKey] = true;
    localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(completedTours));
  }, [tourKey]);

  const resetAllTours = useCallback(() => {
    localStorage.removeItem(TOUR_STORAGE_KEY);
  }, []);

  const handleJoyrideCallback = useCallback(
    (data) => {
      const { action, status, index, type, error } = data;
      if (error) {
        console.warn("[useTour] Error in Joyride callback:", error);
        if (error.message && error.message.includes("null")) {
          setTimeout(() => {
            setStepIndex(index + 1);
            setRun(true);
          }, 300);
        }
        return;
      }

      if (status === "finished" || status === "skipped") {
        markTourAsCompleted();
        setRun(false);
        return;
      }

      if (type === "step:after") {
        if (action === "next" || action === "start") {
          setStepIndex(index + 1);
        } else if (action === "prev") {
          setStepIndex(Math.max(index - 1, 0));
        } else if (action === "close") {
          setRun(false);
          markTourAsCompleted();
        }
      }
    },
    [markTourAsCompleted],
  );

  return {
    run,
    stepIndex,
    startTour,
    stopTour,
    resetTour,
    resetAllTours,
    handleJoyrideCallback,
    goToStep,
    nextStep,
  };
};
