import { React, useEffect, useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import { FormControl, InputLabel, Grid, MenuItem, Select } from "@mui/material";
import { getHyperparameterPlot as getHyperparameterPlotRequest } from "../../../api/run";
import { enqueueSnackbar } from "notistack";

function ResultsTabHyperparameters({ runData }) {
  const [displayMode, setDisplayMode] = useState("nested-list");
  const [historicalPlot, setHistoricalPlot] = useState([]);
  const [slicePlot, setSlicePlot] = useState([]);
  const [contourPlot, setContourPlot] = useState([]);
  const [importancePlot, setImportancePlot] = useState([]);
  function parsePlot(plot) {
    const formattedPlot = JSON.parse(plot);
    const data = formattedPlot.data;
    const layout = formattedPlot.layout;
    return formattedPlot;
  }
  const optimizables = Object.keys(runData.parameters).filter(
    (key) => runData.parameters[key].optimize === true,
  ).length;
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
      } else {
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
      enqueueSnackbar("Error while trying to obtain the run data");
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
    getHyperparameterPlot();
  }, []);
  return (
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
