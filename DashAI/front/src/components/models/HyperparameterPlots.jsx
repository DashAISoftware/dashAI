import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import { Grid, CircularProgress, Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { getHyperparameterPlot as getHyperparameterPlotRequest } from "../../api/run";
import { enqueueSnackbar } from "notistack";
import { checkHowManyOptimazers } from "../../utils/schema";
import { applyThemeToLayout } from "../../utils/plotlyTheme";

function HyperparameterPlots({ run }) {
  const theme = useTheme();
  const [historicalPlot, setHistoricalPlot] = useState(null);
  const [slicePlot, setSlicePlot] = useState(null);
  const [contourPlot, setContourPlot] = useState(null);
  const [importancePlot, setImportancePlot] = useState(null);
  const [loading, setLoading] = useState(true);

  const themedHistoricalLayout = useMemo(
    () => applyThemeToLayout(historicalPlot?.layout, theme),
    [historicalPlot, theme],
  );
  const themedSliceLayout = useMemo(
    () => applyThemeToLayout(slicePlot?.layout, theme),
    [slicePlot, theme],
  );
  const themedContourLayout = useMemo(
    () => applyThemeToLayout(contourPlot?.layout, theme),
    [contourPlot, theme],
  );
  const themedImportanceLayout = useMemo(
    () => applyThemeToLayout(importancePlot?.layout, theme),
    [importancePlot, theme],
  );

  const parsePlot = (plot) => {
    return JSON.parse(plot);
  };

  const optimizables = checkHowManyOptimazers({
    params: run.parameters,
  });

  const getHyperparameterPlot = async () => {
    try {
      setLoading(true);
      if (optimizables >= 2) {
        const [historical, slice, contour, importance] = await Promise.all([
          getHyperparameterPlotRequest(run.id, 1),
          getHyperparameterPlotRequest(run.id, 2),
          getHyperparameterPlotRequest(run.id, 3),
          getHyperparameterPlotRequest(run.id, 4),
        ]);

        setHistoricalPlot(parsePlot(historical));
        setSlicePlot(parsePlot(slice));
        setContourPlot(parsePlot(contour));
        setImportancePlot(parsePlot(importance));
      } else if (optimizables === 1) {
        const [historical, slice] = await Promise.all([
          getHyperparameterPlotRequest(run.id, 1),
          getHyperparameterPlotRequest(run.id, 2),
        ]);

        setHistoricalPlot(parsePlot(historical));
        setSlicePlot(parsePlot(slice));
      }
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain hyperparameter plots", {
        variant: "error",
      });
      console.error("Error loading hyperparameter plots:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (run.status === 3) {
      getHyperparameterPlot();
    } else {
      setLoading(false);
    }
  }, [run.id, run.status, run.parameters]);

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (run.status === 2 || run.status === 1) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Typography color="textSecondary">
          Training in progress. Hyperparameter plots will be available when
          training completes.
        </Typography>
      </Box>
    );
  }

  if (run.status === 4) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Typography color="error">
          Run failed. No hyperparameter plots available.
        </Typography>
      </Box>
    );
  }

  if (run.status === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Typography color="textSecondary">
          Run not started. No hyperparameter plots available.
        </Typography>
      </Box>
    );
  }

  if (!historicalPlot && !slicePlot) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Typography color="textSecondary">
          No hyperparameter plots available.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Grid container spacing={4} direction="column">
        {historicalPlot && (
          <Grid sx={{ width: "100%" }}>
            <Plot
              key={`historical-${run.id}`}
              data={historicalPlot.data}
              layout={{
                ...themedHistoricalLayout,
                width: undefined,
                height: 380,
              }}
              config={{ responsive: true, displayModeBar: true }}
              style={{ width: "100%", height: "380px" }}
            />
          </Grid>
        )}

        {slicePlot && (
          <Grid sx={{ width: "100%" }}>
            <Plot
              key={`slice-${run.id}`}
              data={slicePlot.data}
              layout={{ ...themedSliceLayout, width: undefined, height: 380 }}
              config={{ responsive: true, displayModeBar: true }}
              style={{ width: "100%", height: "380px" }}
            />
          </Grid>
        )}

        {optimizables >= 2 && contourPlot && (
          <Grid sx={{ width: "100%" }}>
            <Plot
              key={`contour-${run.id}`}
              data={contourPlot.data}
              layout={{ ...themedContourLayout, width: undefined, height: 380 }}
              config={{ responsive: true, displayModeBar: true }}
              style={{ width: "100%", height: "380px" }}
            />
          </Grid>
        )}

        {optimizables >= 2 && importancePlot && (
          <Grid sx={{ width: "100%" }}>
            <Plot
              key={`importance-${run.id}`}
              data={importancePlot.data}
              layout={{
                ...themedImportanceLayout,
                width: undefined,
                height: 380,
              }}
              config={{ responsive: true, displayModeBar: true }}
              style={{ width: "100%", height: "380px" }}
            />
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

HyperparameterPlots.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
    status: PropTypes.number.isRequired,
    parameters: PropTypes.object.isRequired,
  }).isRequired,
};

export default HyperparameterPlots;
