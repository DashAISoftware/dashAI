import React from "react";
import PropTypes from "prop-types";
import { Grid, Typography } from "@mui/material";
import ResultsTabParametersDisplayList from "./ResultsTabParametersDisplayList";
import { useTranslation } from "react-i18next";

function ResultsTabParametersDisplay({ displayMode, runData }) {
  const { t } = useTranslation(["common"]);

  return (
    <Grid>
      {displayMode === "nested-list" && (
        <ResultsTabParametersDisplayList
          name={t("common:parameters")}
          value={runData.parameters}
        />
      )}

      {displayMode === "json" && (
        <Typography variant="body1" component="pre">
          {JSON.stringify(runData.parameters, null, 4)}
        </Typography>
      )}
    </Grid>
  );
}

ResultsTabParametersDisplay.propTypes = {
  displayMode: PropTypes.oneOf(["nested-list", "json"]).isRequired,
  runData: PropTypes.shape({
    parameters: PropTypes.objectOf(
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
        PropTypes.bool,
        PropTypes.object,
      ]),
    ),
  }).isRequired,
};

export default ResultsTabParametersDisplay;
