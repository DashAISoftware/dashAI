import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { IconButton } from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import ResultsDialogLayout from "./components/ResultsDialogLayout";
import TimestampWrapper from "../../components/shared/TimestampWrapper";
import { TIMESTAMP_KEYS } from "../../constants/timestamp";
import { useTourContext } from "../../components/tour/TourProvider";

function Results({ experiment, handleDeleteExperiment }) {
  const [open, setOpen] = useState(false);
  const [showTable, setShowTable] = useState(true);
  const tourContext = useTourContext();

  const handleOpen = () => {
    setOpen(true);
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 300);
    }
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleShowTable = () => {
    setShowTable(true);
  };

  const handleShowGraphs = () => {
    setShowTable(false);
  };

  return (
    <>
      <TimestampWrapper eventName={TIMESTAMP_KEYS.experiments.showResults}>
        <IconButton onClick={handleOpen} data-tour="exp-view-results-button">
          <VisibilityIcon />
        </IconButton>
      </TimestampWrapper>

      {open && (
        <ResultsDialogLayout
          experiment={experiment}
          open={open}
          onClose={handleClose}
          showTable={showTable}
          handleShowTable={handleShowTable}
          handleShowGraphs={handleShowGraphs}
          handleDeleteExperiment={handleDeleteExperiment}
        />
      )}
    </>
  );
}

Results.propTypes = {
  experiment: PropTypes.shape({
    name: PropTypes.string,
    id: PropTypes.number,
  }).isRequired,
};

export default Results;
