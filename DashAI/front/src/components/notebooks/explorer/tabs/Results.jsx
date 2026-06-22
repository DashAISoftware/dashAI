import React from "react";
import { Box, CircularProgress } from "@mui/material";
import { visualizersKeys } from "../useExplorerResults";
import ClusteringProfileVisualizer from "../visualizations/ClusteringProfileVisualizer";
import ImageVisualizer from "../visualizations/ImageVisualizer";
import PlotlyJsonVisualizer from "../visualizations/PlotlyJsonVisualizer";
import TabularVisualizer from "../visualizations/TabularVisualizer";

/**
 * Results component to render the results of the exploration
 * @param {Object} props
 * @param {Number} props.id The id of the exploration
 * @param {Boolean} props.minimalist Whether to render in minimalist mode with fixed dimensions
 */
function Results({ id, minimalist = false, loading, data, dataType }) {
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

      {!loading && dataType === visualizersKeys.tabular && (
        <TabularVisualizer
          loading={loading}
          columns={data.columns}
          rows={data.rows}
          minimalist={minimalist}
        />
      )}

      {!loading && dataType === visualizersKeys.plotly_json && (
        <PlotlyJsonVisualizer data={data} minimalist={minimalist} />
      )}

      {!loading && dataType === visualizersKeys.image_base64 && (
        <ImageVisualizer
          data={`data:image/png;base64,${data}`}
          minimalist={minimalist}
        />
      )}

      {!loading && dataType === visualizersKeys.image_url && (
        <ImageVisualizer data={data} minimalist={minimalist} />
      )}

      {!loading && dataType === visualizersKeys.clustering_profile && (
        <ClusteringProfileVisualizer data={data} minimalist={minimalist} />
      )}
    </Box>
  );
}

export default Results;
