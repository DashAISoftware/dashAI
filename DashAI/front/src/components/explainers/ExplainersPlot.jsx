import { React, useEffect, useState } from "react";
import {
  FormControl,
  InputLabel,
  Grid,
  MenuItem,
  Select,
  CircularProgress,
  Box,
} from "@mui/material";
import Plot from "react-plotly.js";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";

import { getExplainerPlot as getExplainerPlotRequest } from "../../api/explainer";
import { useTranslation } from "react-i18next";

export default function ExplainersPlot({ explainer, scope }) {
  const { enqueueSnackbar } = useSnackbar();
  const [explainersPlots, setExplainersPlots] = useState([]);
  const [currentPlot, setCurrentPlot] = useState(0);
  const [loading, setLoading] = useState(true);
  const isLocal = scope === "local";
  const { t } = useTranslation(["explainers"]);
  function parseExplanationPlot(explanation) {
    const formattedPlot = JSON.parse(JSON.stringify(explanation));
    return formattedPlot.map(JSON.parse);
  }

  const getExplainerPlot = async () => {
    setLoading(true);
    try {
      const explainersPlots = await getExplainerPlotRequest(
        explainer.id,
        scope,
      );
      const parsedExplainersPlot = parseExplanationPlot(explainersPlots);
      setExplainersPlots(parsedExplainersPlot);
    } catch (error) {
      enqueueSnackbar(t("explainers:error.fetchExplainers"), {
        variant: "error",
      });
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (explainer.status === 3) {
      getExplainerPlot();
    }
  }, [explainer.status]);

  return (
    <Grid container flexDirection={"row"} justifyContent={"space-between"}>
      <Grid size={{ xs: 8 }}>
        {!loading && isLocal && (
          <FormControl variant="outlined" sx={{ minWidth: "200px" }}>
            <InputLabel id="select-type-label">Select an instance</InputLabel>
            <Select
              id="select-type"
              value={currentPlot}
              onChange={(event) => setCurrentPlot(event.target.value)}
              label="class"
              autoWidth
            >
              {explainersPlots.map((_, i) => (
                <MenuItem key={i} value={i}>
                  {t("explainers:label.instanceNumber", { number: i + 1 })}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </Grid>
      <Grid size={{ xs: 8 }}>
        {!loading && explainer.status === 3 ? (
          <Plot
            data={explainersPlots[currentPlot].data}
            layout={{
              ...explainersPlots[currentPlot].layout,
              width: 730,
              height: 380,
            }}
            config={{ staticPlot: false }}
          />
        ) : explainer.status === 4 ? (
          <Box>{t("explainers:error.explainerFailed")}</Box>
        ) : (
          <Box sx={{ display: "flex", justifyContent: "flex-start", p: 2 }}>
            <CircularProgress />
          </Box>
        )}
      </Grid>
    </Grid>
  );
}

ExplainersPlot.propTypes = {
  explainer: PropTypes.shape({
    explainer_name: PropTypes.string,
    id: PropTypes.number,
    parameters: PropTypes.objectOf(
      PropTypes.oneOfType([
        PropTypes.number,
        PropTypes.string,
        PropTypes.arrayOf(PropTypes.string),
      ]),
    ),
    status: PropTypes.number,
    runId: PropTypes.number,
    explanationPath: PropTypes.string,
    plot_path: PropTypes.string,
    name: PropTypes.string,
    created: PropTypes.string,
  }).isRequired,
  scope: PropTypes.string.isRequired,
};
