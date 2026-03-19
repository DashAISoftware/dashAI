import { React, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import { Grid, CircularProgress, Box } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { getHyperparameterPlot as getHyperparameterPlotRequest } from "../../../api/run";
import { enqueueSnackbar } from "notistack";
import { checkHowManyOptimazers } from "../../../utils/schema";
import { applyThemeToLayout } from "../../../utils/plotlyTheme";
import { useTranslation } from "react-i18next";

function ResultsTabHyperparameters({ runData }) {
  const theme = useTheme();
  const [loading, setLoading] = useState(false);
  const [historicalPlot, setHistoricalPlot] = useState(null);
  const [slicePlot, setSlicePlot] = useState(null);
  const [contourPlot, setContourPlot] = useState(null);
  const [importancePlot, setImportancePlot] = useState(null);
  const { t } = useTranslation(["models"]);

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

  function parsePlot(plot) {
    return JSON.parse(plot);
  }
  const optimizables = checkHowManyOptimazers({
    params: runData.parameters,
  });

  const getHyperparameterPlot = async () => {
    setLoading(true);
    try {
      if (optimizables >= 2) {
        const [historicalPlot, slicePlot, contourPlot, importancePlot] =
          await Promise.all([
            getHyperparameterPlotRequest(runData.id, 1),
            getHyperparameterPlotRequest(runData.id, 2),
            getHyperparameterPlotRequest(runData.id, 3),
            getHyperparameterPlotRequest(runData.id, 4),
          ]);
        setHistoricalPlot(parsePlot(historicalPlot));
        setSlicePlot(parsePlot(slicePlot));
        setContourPlot(parsePlot(contourPlot));
        setImportancePlot(parsePlot(importancePlot));
      } else if (optimizables === 1) {
        const [historicalPlot, slicePlot] = await Promise.all([
          getHyperparameterPlotRequest(runData.id, 1),
          getHyperparameterPlotRequest(runData.id, 2),
        ]);
        setHistoricalPlot(parsePlot(historicalPlot));
        setSlicePlot(parsePlot(slicePlot));
      }
    } catch (error) {
      enqueueSnackbar(t("models:error.errorFetchingRunData"));
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Reques error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (runData.status !== 3) return; // Finished
    getHyperparameterPlot();
  }, [runData]);

  if (loading || runData.status === 1 || runData.status === 2) {
    return (
      <Box
        sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return runData.status === 4 ? ( // Failed
    <Box>{t("models:label.runFailedNoHyperparameterPlots")}</Box>
  ) : runData.status === 0 ? ( // Not Started
    <Box>{t("models:label.runNotStartedNoHyperparameterPlots")}</Box>
  ) : !historicalPlot ? (
    <Box>{t("models:label.noHyperparameterPlotsAvailable")}</Box>
  ) : (
    <Grid container spacing={2} direction="column">
      <Grid container direction="column">
        <Plot
          data={historicalPlot?.data}
          layout={{ ...themedHistoricalLayout, width: 900, height: 380 }}
          config={{ staticPlot: false }}
        />
      </Grid>
      <Grid container direction="column">
        <Plot
          data={slicePlot?.data}
          layout={{ ...themedSliceLayout, width: 900, height: 380 }}
          config={{ staticPlot: false }}
        />
      </Grid>
      {optimizables >= 2 && (
        <>
          <Grid container direction="column">
            <Plot
              data={contourPlot?.data}
              layout={{ ...themedContourLayout, width: 900, height: 380 }}
              config={{ staticPlot: false }}
            />
          </Grid>
          <Grid container direction="column">
            <Plot
              data={importancePlot?.data}
              layout={{ ...themedImportanceLayout, width: 900, height: 380 }}
              config={{ staticPlot: false }}
            />
          </Grid>
        </>
      )}
    </Grid>
  );
}

ResultsTabHyperparameters.propTypes = {
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

export default ResultsTabHyperparameters;
