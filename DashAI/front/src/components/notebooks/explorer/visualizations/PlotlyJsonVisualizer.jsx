import React, { useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import { Box } from "@mui/material";
import Dialog from "@mui/material/Dialog";
const MIN_WIDTH = 300;
const MIN_HEIGHT_MINIMALIST = 200;
const MIN_HEIGHT_NORMAL = 500;

function PlotlyJsonVisualizer({ data, minimalist = false }) {
  const [expanded, setExpanded] = useState(false);

  // Parse JSON if data is a string
  const parsedData = typeof data === "string" ? JSON.parse(data) : data;

  // Remove the name if minimalist
  const plotData = minimalist
    ? {
        ...parsedData,
        layout: {
          ...parsedData.layout,
          title: "",
        },
      }
    : {
        ...parsedData,
        layout: { ...parsedData.layout, height: MIN_HEIGHT_NORMAL },
      };

  const toggleFullscreen = () => {
    setExpanded(!expanded);
  };

  const plotConfig = {
    responsive: true,
    displaylogo: false,
    displayModeBar: true,
    modeBarButtonsToRemove: minimalist
      ? [
          "sendDataToCloud",
          "lasso2d",
          "select2d",
          "zoom2d",
          "pan2d",
          "autoScale2d",
        ]
      : ["sendDataToCloud", "lasso2d", "select2d"],
    modeBarButtonsToAdd: minimalist
      ? []
      : [
          {
            name: "fullscreen",
            title: "Fullscreen",
            icon: {
              width: 1000,
              path: "M128 32H32C14.31 32 0 46.31 0 64v96c0 17.69 14.31 32 32 32s32-14.31 32-32V96h64c17.69 0 32-14.31 32-32S145.7 32 128 32zM416 32h-96c-17.69 0-32 14.31-32 32s14.31 32 32 32h64v64c0 17.69 14.31 32 32 32s32-14.31 32-32V64C448 46.31 433.7 32 416 32zM128 416H64v-64c0-17.69-14.31-32-32-32s-32 14.31-32 32v96c0 17.69 14.31 32 32 32h96c17.69 0 32-14.31 32-32S145.7 416 128 416zM416 320c-17.69 0-32 14.31-32 32v64h-64c-17.69 0-32 14.31-32 32s14.31 32 32 32h96c17.69 0 32-14.31 32-32v-96C448 334.3 433.7 320 416 320z",
              transform: "scale(0.03)",
            },
            click: () => {
              toggleFullscreen();
            },
          },
          "resetScale2d",
        ],
    toImageButtonOptions: {
      format: "png",
      filename: "dashai-plot",
      height: 800,
      width: 1200,
      scale: 1,
    },
  };

  const fullscreenConfig = {
    ...plotConfig,
    scrollZoom: true,
    modeBarButtonsToAdd: [
      {
        name: "exit-fullscreen",
        title: "Exit fullscreen",
        icon: {
          width: 1000,
          path: "M5.5 0a.5.5 0 0 1 .5.5v4A1.5 1.5 0 0 1 4.5 6h-4a.5.5 0 0 1 0-1h4a.5.5 0 0 0 .5-.5v-4a.5.5 0 0 1 .5-.5m5 0a.5.5 0 0 1 .5.5v4a.5.5 0 0 0 .5.5h4a.5.5 0 0 1 0 1h-4A1.5 1.5 0 0 1 10 4.5v-4a.5.5 0 0 1 .5-.5M0 10.5a.5.5 0 0 1 .5-.5h4A1.5 1.5 0 0 1 6 11.5v4a.5.5 0 0 1-1 0v-4a.5.5 0 0 0-.5-.5h-4a.5.5 0 0 1-.5-.5m10 1a1.5 1.5 0 0 1 1.5-1.5h4a.5.5 0 0 1 0 1h-4a.5.5 0 0 0-.5.5v4a.5.5 0 0 1-1 0z",
        },
        click: function () {
          setExpanded(false);
        },
      },
      "zoom2d",
      "pan2d",
      "resetScale2d",
    ],
  };

  const plotLayout = {
    ...plotData.layout,
    margin: minimalist
      ? {
          l: 40,
          r: 20,
          t: 30,
          b: 40,
          ...plotData.layout?.margin,
        }
      : {
          l: 60,
          r: 30,
          t: 50,
          b: 60,
          ...plotData.layout?.margin,
        },
    autosize: true,
    font: {
      size: minimalist ? 10 : 12,
      ...plotData.layout?.font,
    },
    title: {
      ...plotData.layout?.title,
      font: {
        size: minimalist ? 12 : 16,
        ...plotData.layout?.title?.font,
      },
    },
  };

  return (
    <React.Fragment>
      <Box
        sx={{
          position: "relative",
          width: "100%",
          minWidth: MIN_WIDTH,
          minHeight: minimalist ? MIN_HEIGHT_MINIMALIST : MIN_HEIGHT_NORMAL,
          height: minimalist ? "100%" : "auto",
          overflow: "hidden",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {!expanded ? (
          <Plot
            id="plotly-graph"
            data={plotData.data}
            layout={plotLayout}
            style={{
              width: "100%",
              // Explicit floor so Plotly never renders at 0 height
              minHeight: minimalist ? MIN_HEIGHT_MINIMALIST : MIN_HEIGHT_NORMAL,
              height: minimalist ? "100%" : MIN_HEIGHT_NORMAL,
            }}
            config={plotConfig}
            useResizeHandler={true}
          />
        ) : (
          <Dialog
            open={expanded}
            fullScreen
            onClose={() => setExpanded(false)}
            slotProps={{
              paper: {
                sx: { bgcolor: "white" },
              },
            }}
          >
            <Plot
              data={plotData.data}
              layout={{
                ...plotData.layout,
                autosize: true,
                margin: {
                  l: 80,
                  r: 40,
                  t: 80,
                  b: 80,
                  ...plotData.layout?.margin,
                },
                font: {
                  size: 14,
                  ...plotData.layout?.font,
                },
                title: {
                  ...plotData.layout?.title,
                  font: {
                    size: 18,
                    ...plotData.layout?.title?.font,
                  },
                },
              }}
              style={{ width: "100vw", height: "100vh" }}
              useResizeHandler={true}
              config={fullscreenConfig}
            />
          </Dialog>
        )}
      </Box>
    </React.Fragment>
  );
}

PlotlyJsonVisualizer.propTypes = {
  data: PropTypes.oneOfType([PropTypes.object, PropTypes.string]).isRequired,
  minimalist: PropTypes.bool,
};

export default PlotlyJsonVisualizer;
