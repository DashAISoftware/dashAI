import { React, useEffect, useMemo, useState } from "react";
import {
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  CircularProgress,
  Box,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import Plot from "react-plotly.js";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";

import { getExplainerPlot as getExplainerPlotRequest } from "../../api/explainer";
import { useTranslation } from "react-i18next";
import { applyThemeToLayout } from "../../utils/plotlyTheme";

export default function ExplainersPlot({ explainer, scope }) {
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [explainersPlots, setExplainersPlots] = useState([]);
  const [currentPlot, setCurrentPlot] = useState(0);
  const [loading, setLoading] = useState(true);
  const isLocal = scope === "local";
  const { t } = useTranslation(["explainers"]);

  const themedLayout = useMemo(() => {
    if (!explainersPlots[currentPlot]) return {};
    return applyThemeToLayout(explainersPlots[currentPlot].layout, theme);
  }, [explainersPlots, currentPlot, theme]);
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
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
      }}
    >
      {!loading && isLocal && (
        <FormControl variant="outlined" sx={{ minWidth: "200px", mb: 1 }}>
          <InputLabel id="select-type-label">Select an instance</InputLabel>
          <Select
            id="select-type"
            value={currentPlot}
            onChange={(event) => setCurrentPlot(event.target.value)}
            label="class"
            autoWidth
          >
            {explainersPlots.map((plot, i) => (
              <MenuItem
                key={plot?.layout?.title?.text ?? `instance-${i}`}
                value={i}
              >
                {t("explainers:label.instanceNumber", { number: i + 1 })}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      {!loading && explainer.status === 3 ? (
        <Plot
          data={explainersPlots[currentPlot].data}
          layout={{
            ...themedLayout,
            width: 700,
            height: 380,
          }}
          config={{ displayModeBar: false }}
        />
      ) : explainer.status === 4 ? (
        <Box sx={{ p: 2 }}>{t("explainers:error.explainerFailed")}</Box>
      ) : (
        <Box sx={{ display: "flex", justifyContent: "flex-start", p: 2 }}>
          <CircularProgress />
        </Box>
      )}
    </Box>
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
