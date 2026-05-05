import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Grid } from "@mui/material";

import ResultsTabMetricsToggle from "./ResultsTabMetricsToggle";
import ResultsTabMetricsRuns from "./ResultsTabMetricsRuns";

/**
 * Component that displays the metrics associated with a run.
 * @param {object} runData object that contains all the necesary info of the
 */
function ResultsTabMetrics({ runData }) {
  const [displaySet, setDisplaySet] = useState("test_metrics");

  return (
    <Grid container direction="column" rowSpacing={2}>
      {/* Toggle to select the set on which the metrics are applied.  */}
      <ResultsTabMetricsToggle
        displaySet={displaySet}
        setDisplaySet={setDisplaySet}
        evaluationStrategy={runData.evaluation_strategy}
      />

      {/* metrics */}
      <ResultsTabMetricsRuns runData={runData} displaySet={displaySet} />
    </Grid>
  );
}

ResultsTabMetrics.propTypes = {
  runData: PropTypes.shape({
    status: PropTypes.number,
    train_metrics: PropTypes.object,
    test_metrics: PropTypes.object,
    validation_metrics: PropTypes.object,
    evaluation_strategy: PropTypes.string,
  }),
  setUpdateDataFlag: PropTypes.func.isRequired,
};

export default ResultsTabMetrics;
