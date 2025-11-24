import { useSnackbar } from "notistack";
import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { getRunById as getRunByIdRequest } from "../../../api/run";
import ResultsDetailsLayout from "./ResultsDetailsLayout";

/**
 * Component that renders multiple tabs to visualize the results of a specific run.
 */
function ResultsDetails({ run, onClose, handleRun }) {
  const [currentTab, setCurrentTab] = useState(0);

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

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

ResultsDetails.defaultProps = {
  run: undefined,
};

export default ResultsDetails;
