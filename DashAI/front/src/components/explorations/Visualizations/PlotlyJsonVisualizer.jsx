import React, { useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import { Box, Slider, Typography } from "@mui/material";
import Dialog from "@mui/material/Dialog";

function PlotlyJsonVisualizer({ data }) {
  const [expanded, setExpanded] = useState(false);
  const [height, setHeight] = useState(500);

  // Parse JSON if data is a string
  const plotData = typeof data === "string" ? JSON.parse(data) : data;

  // Función para manejar el botón de pantalla completa personalizado
  const toggleFullscreen = () => {
    setExpanded(!expanded);
  };

  // Configuración para añadir botón personalizado a la barra de herramientas de Plotly
  const plotConfig = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["sendDataToCloud", "lasso2d", "select2d"],
    modeBarButtonsToAdd: [
      {
        name: "fullscreen",
        title: "Fullscreen",
        icon: {
          width: 1000,
          path: "M128 32H32C14.31 32 0 46.31 0 64v96c0 17.69 14.31 32 32 32s32-14.31 32-32V96h64c17.69 0 32-14.31 32-32S145.7 32 128 32zM416 32h-96c-17.69 0-32 14.31-32 32s14.31 32 32 32h64v64c0 17.69 14.31 32 32 32s32-14.31 32-32V64C448 46.31 433.7 32 416 32zM128 416H64v-64c0-17.69-14.31-32-32-32s-32 14.31-32 32v96c0 17.69 14.31 32 32 32h96c17.69 0 32-14.31 32-32S145.7 416 128 416zM416 320c-17.69 0-32 14.31-32 32v64h-64c-17.69 0-32 14.31-32 32s14.31 32 32 32h96c17.69 0 32-14.31 32-32v-96C448 334.3 433.7 320 416 320z",
          transform: "scale(0.03)",
        },
        click: function () {
          toggleFullscreen();
        },
      },
      "resetScale2d",
    ],
    toImageButtonOptions: {
      format: "svg",
      filename: "dashai-plot",
      height: 800,
      width: 1200,
      scale: 1,
    },
  };

  // Configuración específica para el modo de pantalla completa
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

  return (
    <React.Fragment>
      <Box sx={{ position: "relative", width: "100%" }}>
        {/* Height control - solo para vista normal */}
        {!expanded && (
          <Box
            sx={{
              position: "absolute",
              top: 25,
              left: 10,
              zIndex: 1,
              width: 150,
              display: "flex",
              alignItems: "center",
            }}
          >
            <Typography
              variant="caption"
              sx={{
                mr: 1,
                color: "rgba(0,0,0,0.6)",
                bgcolor: "rgba(255,255,255,0.9)",
                px: 1,
                borderRadius: 1,
                border: "1px solid rgba(0,0,0,0.1)",
              }}
            >
              Height
            </Typography>
            <Slider
              value={height}
              onChange={(e, val) => setHeight(val)}
              min={300}
              max={1000}
              step={50}
              size="small"
              sx={{
                width: 80,
                "& .MuiSlider-rail": {
                  bgcolor: "rgba(0,0,0,0.2)",
                },
                "& .MuiSlider-track": {
                  bgcolor: "primary.main",
                },
                "& .MuiSlider-thumb": {
                  bgcolor: "primary.main",
                  border: "2px solid white",
                  boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                },
              }}
            />
          </Box>
        )}

        {/* Plot principal o Dialog en pantalla completa */}
        {!expanded ? (
          <Plot
            id="plotly-graph"
            data={plotData.data}
            layout={{
              ...plotData.layout,
              paper_bgcolor: plotData.layout?.paper_bgcolor || "white",
              plot_bgcolor: plotData.layout?.plot_bgcolor || "white",
              height: height,
              margin: {
                l: 60,
                r: 30,
                t: 50,
                b: 60,
                ...plotData.layout?.margin,
              },
              autosize: true,
            }}
            style={{ width: "100%", height: `${height}px` }}
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
                paper_bgcolor: plotData.layout?.paper_bgcolor || "white",
                plot_bgcolor: plotData.layout?.plot_bgcolor || "white",
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
};

export default PlotlyJsonVisualizer;
