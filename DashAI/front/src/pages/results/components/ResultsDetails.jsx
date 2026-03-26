import { useSnackbar } from "notistack";
import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { getRunById as getRunByIdRequest } from "../../../api/run";
import ResultsDetailsLayout from "./ResultsDetailsLayout";
import { checkIfHaveOptimazers } from "../../../utils/schema";

/**
 * Component that renders multiple tabs to visualize the results of a specific run.
 */
function ResultsDetails({ run, onClose, handleRun }) {
  const [currentTab, setCurrentTab] = useState(0);
  const optimizers = run ? checkIfHaveOptimazers(run.parameters) : null;

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  useEffect(() => {
    if (!optimizers) {
      setCurrentTab(0);
    }
  }, [run?.id]);

  if (!run) {
    onClose();
    return null;
  }

  return (
    <ResultsDetailsLayout
      runData={run}
      currentTab={currentTab}
      handleTabChange={handleTabChange}
      handleCloseCustomLayout={onClose}
      handleRun={handleRun}
    />
  );
}

ResultsDetails.propTypes = {
  run: PropTypes.object,
};

export default ResultsDetails;
