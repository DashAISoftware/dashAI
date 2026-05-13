import React from "react";
import PropTypes from "prop-types";
import {
  Alert,
  AlertTitle,
  Box,
  Divider,
  Grid,
  LinearProgress,
  Link,
  Paper,
  Typography,
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { getDisplaySetName } from "../constants/getDisplaySetName";
import { Trans } from "react-i18next";

function ResultsTabMetricsRuns({ runData, displaySet }) {
  return (
    <Grid>
      <Paper sx={{ borderRadius: 4 }}>
        <Grid container direction="column" rowSpacing={4} sx={{ mt: 4 }}>
          {runData[displaySet] === null ? (
            runData.status === 3 ? (
              <Box sx={{ width: "100%" }}>
                <LinearProgress />
              </Box>
            ) : (
              <Alert severity="warning" sx={{ mb: 4 }}>
                <AlertTitle>
                  {t("models:label.thereAreNoMetricsForThisRun", {
                    set: getDisplaySetName(displaySet),
                  })}
                </AlertTitle>
                <Trans i18nKey="models:label.runExperimentToSeeMetrics">
                  Go to
                  <Link component={RouterLink} to="/app/experiments">
                    experiments tab
                  </Link>
                  to run your experiment.
                </Trans>
              </Alert>
            )
          ) : Object.keys(runData[displaySet]).length === 0 ? (
            <Alert severity="error" sx={{ mb: 4 }}>
              <AlertTitle>Error</AlertTitle>
              <Typography variant="body1">
                {t("models:label.metricsEmptyForDisplaySet", {
                  set: getDisplaySetName(displaySet),
                })}
              </Typography>
            </Alert>
          ) : (
            Object.keys(runData[displaySet]).map((metric) => (
              <Grid key={metric} sx={{ px: 4, py: 4, width: "100%" }}>
                <Typography variant="body2">{metric}</Typography>
                <Typography variant="body2" sx={{ float: "right" }}>
                  {runData[displaySet][metric].toFixed(2)}
                </Typography>
                <Divider sx={{ mt: 4 }} />
              </Grid>
            ))
          )}
        </Grid>
      </Paper>
    </Grid>
  );
}

ResultsTabMetricsRuns.propTypes = {
  runData: PropTypes.object.isRequired,
  displaySet: PropTypes.string.isRequired,
};

export default ResultsTabMetricsRuns;
