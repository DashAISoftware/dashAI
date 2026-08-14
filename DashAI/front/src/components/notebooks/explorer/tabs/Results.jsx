import React from "react";
import { Box, CircularProgress, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { visualizersKeys } from "../../../../utils/artifactVisualizerData";
import ImageVisualizer from "../visualizations/ImageVisualizer";
import PlotlyJsonVisualizer from "../visualizations/PlotlyJsonVisualizer";
import TabularVisualizer from "../visualizations/TabularVisualizer";

/**
 * Results component to render the results of the exploration
 * @param {Object} props
 * @param {Number} props.id The id of the exploration
 * @param {Boolean} props.minimalist Whether to render in minimalist mode with fixed dimensions
 * @param {Object} props.error Error raised while fetching the results, if any
 */
function Results({ id, minimalist = false, loading, data, dataType, error }) {
  const { t } = useTranslation(["datasets"]);

  if (!id) return null;

  const containerStyles = minimalist
    ? {
        height: "100%",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 1,
        overflow: "hidden",
        flexDirection: "column",
      }
    : {
        height: "100%",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "auto",
        flexDirection: "column",
        flex: 1,
      };

  return (
    <Box sx={containerStyles}>
      {loading && <CircularProgress size={minimalist ? 24 : undefined} />}

      {!loading && error && (
        <Typography
          variant="body2"
          sx={{ color: "text.secondary", textAlign: "center", p: 2 }}
        >
          {t("datasets:error.explorerResultsUnavailable")}
        </Typography>
      )}

      {!loading && !error && dataType === visualizersKeys.tabular && (
        <TabularVisualizer
          loading={loading}
          columns={data.columns}
          rows={data.rows}
          minimalist={minimalist}
        />
      )}

      {!loading && !error && dataType === visualizersKeys.plotly_json && (
        <PlotlyJsonVisualizer data={data} minimalist={minimalist} />
      )}

      {!loading && !error && dataType === visualizersKeys.image_base64 && (
        <ImageVisualizer
          data={`data:image/png;base64,${data}`}
          minimalist={minimalist}
        />
      )}

      {!loading && !error && dataType === visualizersKeys.image_url && (
        <ImageVisualizer data={data} minimalist={minimalist} />
      )}
    </Box>
  );
}

export default Results;
