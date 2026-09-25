import { useState, useCallback, useEffect, useRef } from "react";

const TOUR_STORAGE_KEY = "dashai_tours_completed";
const TARGET_POLL_MS = 200;
const TARGET_WAIT_MS = 8000;

const isTargetVisible = (selector) => {
  const element = document.querySelector(selector);
  if (!element) return false;
  for (
    let node = element;
    node && node !== document.body;
    node = node.parentElement
  ) {
    const { display, visibility } = getComputedStyle(node);
    if (display === "none" || visibility === "hidden") return false;
  }
  return true;
};

export const useTour = (tourKey) => {
  const [run, setRun] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const runRef = useRef(false);
  const missingRef = useRef({ index: null, since: 0, timer: null });

  useEffect(() => {
    runRef.current = run;
  }, [run]);

  const clearMissingWatch = useCallback(() => {
    clearInterval(missingRef.current.timer);
    missingRef.current = { index: null, since: 0, timer: null };
  }, []);

  useEffect(() => clearMissingWatch, [clearMissingWatch]);

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
    clearMissingWatch();
    setStepIndex(0);
    setRun(true);
  }, [clearMissingWatch]);

  const stopTour = useCallback(() => {
    clearMissingWatch();
    setRun(false);
  }, [clearMissingWatch]);

  const resetTour = useCallback(() => {
    clearMissingWatch();
    setStepIndex(0);
    setRun(false);
  }, [clearMissingWatch]);

  const goToStep = useCallback((step) => {
    setStepIndex(step);
  }, []);

  const resumeAtStep = useCallback((step) => {
    setRun(false);
    setTimeout(() => {
      setStepIndex(step);
      setRun(true);
    }, 80);
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

  const completeTour = useCallback(() => {
    clearMissingWatch();
    markTourAsCompleted();
    setRun(false);
  }, [clearMissingWatch, markTourAsCompleted]);

  const resetAllTours = useCallback(() => {
    localStorage.removeItem(TOUR_STORAGE_KEY);
  }, []);

  const watchMissingTarget = useCallback(
    (target, index, action) => {
      const watch = missingRef.current;
      clearInterval(watch.timer);
      const since = watch.index === index ? watch.since : Date.now();
      const timer = setInterval(() => {
        if (!runRef.current) {
          clearMissingWatch();
        } else if (isTargetVisible(target)) {
          clearInterval(timer);
          missingRef.current.timer = null;
          resumeAtStep(index);
        } else if (Date.now() - since >= TARGET_WAIT_MS) {
          clearMissingWatch();
          setStepIndex(action === "prev" ? Math.max(index - 1, 0) : index + 1);
        }
      }, TARGET_POLL_MS);
      missingRef.current = { index, since, timer };
    },
    [clearMissingWatch, resumeAtStep],
  );

  const handleJoyrideCallback = useCallback(
    (data) => {
      const { action, status, index, type, step } = data;
      if (type === "error:target_not_found") {
        watchMissingTarget(step.target, index, action);
        return;
      }

      if (type === "tooltip") {
        clearMissingWatch();
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
    [markTourAsCompleted, watchMissingTarget, clearMissingWatch],
  );

  return {
    run,
    stepIndex,
    startTour,
    stopTour,
    completeTour,
    resetTour,
    resetAllTours,
    handleJoyrideCallback,
    goToStep,
    nextStep,
    resumeAtStep,
  };
};
