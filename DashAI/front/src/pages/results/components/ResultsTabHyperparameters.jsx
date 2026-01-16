import { React, useEffect, useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import {
  FormControl,
  InputLabel,
  Grid,
  MenuItem,
  Select,
  CircularProgress,
  Box,
} from "@mui/material";
import { getHyperparameterPlot as getHyperparameterPlotRequest } from "../../../api/run";
import { enqueueSnackbar } from "notistack";
import { checkHowManyOptimazers } from "../../../utils/schema";
import { useTranslation } from "react-i18next";

function ResultsTabHyperparameters({ runData }) {
  const [displayMode, setDisplayMode] = useState("nested-list");
  const [historicalPlot, setHistoricalPlot] = useState([]);
  const [slicePlot, setSlicePlot] = useState([]);
  const [contourPlot, setContourPlot] = useState([]);
  const [importancePlot, setImportancePlot] = useState([]);
  const { t } = useTranslation(["models"]);

  function parsePlot(plot) {
    const formattedPlot = JSON.parse(plot);
    const data = formattedPlot.data;
    const layout = formattedPlot.layout;
    return formattedPlot;
  }
  const optimizables = checkHowManyOptimazers({
    params: runData.parameters,
  });

  const getHyperparameterPlot = async () => {
    try {
      if (optimizables >= 2) {
        const historicalPlot = await getHyperparameterPlotRequest(
          runData.id,
          1,
        );
        const slicePlot = await getHyperparameterPlotRequest(runData.id, 2);
        const contourPlot = await getHyperparameterPlotRequest(runData.id, 3);
        const importancePlot = await getHyperparameterPlotRequest(
          runData.id,
          4,
        );
        const parsedHistoricalPlot = parsePlot(historicalPlot);
        const parsedSlicePlot = parsePlot(slicePlot);
        const parsedContourPlot = parsePlot(contourPlot);
        const parsedImportancePlot = parsePlot(importancePlot);
        setHistoricalPlot(parsedHistoricalPlot);
        setSlicePlot(parsedSlicePlot);
        setContourPlot(parsedContourPlot);
        setImportancePlot(parsedImportancePlot);
      } else if (optimizables === 1) {
        const historicalPlot = await getHyperparameterPlotRequest(
          runData.id,
          1,
        );
        const slicePlot = await getHyperparameterPlotRequest(runData.id, 2);
        const parsedHistoricalPlot = parsePlot(historicalPlot);
        const parsedSlicePlot = parsePlot(slicePlot);
        setHistoricalPlot(parsedHistoricalPlot);
        setSlicePlot(parsedSlicePlot);
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
    }
  };

  useEffect(() => {
    if (runData.status !== "Finished") return;
    getHyperparameterPlot();
  }, [runData]);

  return runData.status === "Started" || runData.status === "Delivered" ? (
    <Box
      sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}
    >
      <CircularProgress />
    </Box>
  ) : runData.status === "Failed" ? (
    <Box>{t("models:label.runFailedNoHyperparameterPlots")}</Box>
  ) : runData.status === "Not Started" ? (
    <Box>{t("models:label.runNotStartedNoHyperparameterPlots")}</Box>
  ) : (
    <Grid container spacing={2} direction="column">
      <Grid container direction="column">
        <Plot
          data={historicalPlot["data"]}
          layout={{
            ...historicalPlot["layout"],
            width: 900,
            height: 380,
          }}
          config={{ staticPlot: false }}
        />
      </Grid>
      <Grid container direction="column">
        <Plot
          data={slicePlot["data"]}
          layout={{
            ...slicePlot["layout"],
            width: 900,
            height: 380,
          }}
          config={{ staticPlot: false }}
        />
      </Grid>
      {optimizables >= 2 && (
        <>
          <Grid container direction="column">
            <Plot
              data={contourPlot["data"]}
              layout={{
                ...contourPlot["layout"],
                width: 900,
                height: 380,
              }}
              config={{ staticPlot: false }}
            />
          </Grid>
          <Grid container direction="column">
            <Plot
              data={importancePlot["data"]}
              layout={{
                ...importancePlot["layout"],
                width: 900,
                height: 380,
              }}
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
