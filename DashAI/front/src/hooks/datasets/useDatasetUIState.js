import { useState, useCallback } from "react";

/**
 * Manages the UI state for dataset module:
 * - step
 * - selectedOption
 * - navigation resets
 */
export function useDatasetUIState() {
  const [step, setStep] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);

  // ---------------- navigation helpers ----------------

  const resetUI = useCallback(() => {
    setStep(0);
    setSelectedOption(null);
  }, []);

  const selectDatasetView = useCallback(() => {
    setStep(0);
    setSelectedOption("dataset");
  }, []);

  const selectNotebookView = useCallback(() => {
    setStep(0);
    setSelectedOption("notebook");
  }, []);

  const goToNotebookCreation = () => {
    setSelectedOption("notebook");
    setStep(1);
  };

  return {
    resetUI,
    goToNotebookCreation,
    selectDatasetView,
    selectNotebookView,
  };
}
