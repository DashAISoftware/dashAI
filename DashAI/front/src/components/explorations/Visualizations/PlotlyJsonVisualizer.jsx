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
          width: 1792,
          path: "M128 320v-192q0-40 28-68t68-28h320q26 0 45 19t19 45-19 45-45 19h-192v128q0 26-19 45t-45 19-45-19-19-45zm0 1152v-192q0-26 19-45t45-19 45 19 19 45v128h192q26 0 45 19t19 45-19 45-45 19h-320q-40 0-68-28t-28-68zm1408-1152v192q0 26-19 45t-45 19-45-19-19-45v-128h-192q-26 0-45-19t-19-45 19-45 45-19h320q40 0 68 28t28 68zm0 1152v-192q0-40-28-68t-68-28h-320q-26 0-45-19t-19-45 19-45 45-19h192v-128q0-26 19-45t45-19 45 19 19 45v192q0 40-28 68t-68 28z",
          ascent: 1664,
          descent: -128,
        },
        click: function () {
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

        {/* Main Plot (non-expanded) */}
        {!expanded ? (
          <Plot
            id="plotly-graph"
            data={plotData.data}
            layout={{
              ...plotData.layout,
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
          // Expanded full-screen view
          <Dialog
            open={expanded}
            fullScreen
            onClose={() => setExpanded(false)}
            PaperProps={{
              sx: { bgcolor: "white" },
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
              config={{
                ...plotConfig,
                scrollZoom: true,
                modeBarButtonsToAdd: [
                  {
                    name: "exit-fullscreen",
                    title: "Exit fullscreen",
                    icon: {
                      width: 1792,
                      path: "M896 960v192q0 40-28 68t-68 28h-320q-26 0-45-19t-19-45 19-45 45-19h192v-128q0-26 19-45t45-19 45 19 19 45zm0-256v-192q0-26-19-45t-45-19-45 19-19 45v128h-192q-26 0-45-19t-19-45 19-45 45-19h320q40 0 68 28t28 68zm640 256v192q0 26-19 45t-45 19-45-19-19-45v-128h-192q-26 0-45-19t-19-45 19-45 45-19h320q40 0 68-28t28-68zm0-256v-192q0-40-28-68t-68-28h-320q-26 0-45-19t-19-45 19-45 45-19h192v-128q0-26 19-45t45-19 45 19 19 45v192q0 40 28 68t68 28z",
                      ascent: 1664,
                      descent: -128,
                    },
                    click: function () {
                      setExpanded(false);
                    },
                  },
                  "zoom2d",
                  "pan2d",
                  "resetScale2d",
                ],
              }}
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
