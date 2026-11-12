import React from "react";
import PropTypes from "prop-types";
import HyperparameterPlots from "../../../components/models/HyperparameterPlots";

function ResultsTabHyperparameters({ runData }) {
  return <HyperparameterPlots run={runData} />;
}

ResultsTabHyperparameters.propTypes = {
  runData: PropTypes.shape({
    id: PropTypes.number.isRequired,
    status: PropTypes.number.isRequired,
  }).isRequired,
};

export default ResultsTabHyperparameters;
