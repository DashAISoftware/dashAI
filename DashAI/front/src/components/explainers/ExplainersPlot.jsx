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

function applyThemeToLayout(baseLayout, theme) {
  const bg = theme.palette.background.paper;
  const textColor = theme.palette.text.primary;
  const gridColor = theme.palette.divider;

  // Strip backend-provided fixed dimensions so our responsive sizing takes over
  // eslint-disable-next-line no-unused-vars
  const { width: _w, height: _h, ...rest } = baseLayout ?? {};

  const axisOverride = {
    gridcolor: gridColor,
    zerolinecolor: gridColor,
  };

  return {
    ...rest,
    paper_bgcolor: bg,
    plot_bgcolor: bg,
    font: {
      ...baseLayout?.font,
      color: textColor,
      family: "Quicksand-Bold, sans-serif",
    },
    xaxis: {
      ...baseLayout?.xaxis,
      ...axisOverride,
      tickfont: { ...baseLayout?.xaxis?.tickfont, color: textColor },
    },
    yaxis: {
      ...baseLayout?.yaxis,
      ...axisOverride,
      tickfont: { ...baseLayout?.yaxis?.tickfont, color: textColor },
    },
    legend: {
      ...baseLayout?.legend,
      bgcolor: bg,
      bordercolor: gridColor,
    },
    title: {
      ...baseLayout?.title,
      font: { ...baseLayout?.title?.font, color: textColor },
    },
    ...(baseLayout?.updatemenus && {
      updatemenus: baseLayout.updatemenus.map((menu) => ({
        ...menu,
        bgcolor:
          theme.palette.ui?.borderLight ?? theme.palette.background.paper,
        bordercolor: gridColor,
        font: { color: "#000000" },
        activecolor: theme.palette.primary.main,
      })),
    }),
    ...(baseLayout?.polar && {
      polar: {
        ...baseLayout.polar,
        bgcolor: bg,
        radialaxis: {
          ...baseLayout.polar.radialaxis,
          gridcolor: gridColor,
          linecolor: gridColor,
          tickfont: {
            ...baseLayout.polar.radialaxis?.tickfont,
            color: textColor,
          },
        },
        angularaxis: {
          ...baseLayout.polar.angularaxis,
          color: textColor,
          gridcolor: gridColor,
          linecolor: gridColor,
        },
      },
    }),
  };
}

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
            {explainersPlots.map((_, i) => (
              <MenuItem key={i} value={i}>
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
          config={{ responsive: false, displayModeBar: false }}
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
