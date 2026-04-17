import React, { useState, useRef } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import { Box, IconButton, Tooltip } from "@mui/material";
import Dialog from "@mui/material/Dialog";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import FullscreenIcon from "@mui/icons-material/Fullscreen";
import FullscreenExitIcon from "@mui/icons-material/FullscreenExit";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";

const MIN_WIDTH = 300;
const MIN_HEIGHT_MINIMALIST = 200;
const MIN_HEIGHT_NORMAL = 500;

function PlotlyJsonVisualizer({ data, minimalist = false }) {
  const [expanded, setExpanded] = useState(false);
  const plotRef = useRef(null);
  const fullscreenPlotRef = useRef(null);

  const parsedData = typeof data === "string" ? JSON.parse(data) : data;

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

  const getPlotly = (ref) => {
    const el = ref?.current?.el;
    if (!el) return null;
    return (
      el._fullLayout?._context?._exportedPlotly ||
      el._fullData?.[0]?._fullLayout?._context?._exportedPlotly ||
      window.Plotly ||
      null
    );
  };

  const relayout = (ref, update) => {
    const el = ref?.current?.el;
    const Plotly = getPlotly(ref);
    if (el && Plotly) Plotly.relayout(el, update);
  };

  const handleZoomIn = (ref) => {
    const el = ref?.current?.el;
    if (!el) return;
    const xRange = el._fullLayout?.xaxis?.range;
    const yRange = el._fullLayout?.yaxis?.range;
    if (xRange && yRange) {
      const xCenter = (xRange[0] + xRange[1]) / 2;
      const yCenter = (yRange[0] + yRange[1]) / 2;
      const xSpan = (xRange[1] - xRange[0]) * 0.25;
      const ySpan = (yRange[1] - yRange[0]) * 0.25;
      relayout(ref, {
        "xaxis.range": [xCenter - xSpan, xCenter + xSpan],
        "yaxis.range": [yCenter - ySpan, yCenter + ySpan],
      });
    }
  };

  const handleZoomOut = (ref) => {
    const el = ref?.current?.el;
    if (!el) return;
    const xRange = el._fullLayout?.xaxis?.range;
    const yRange = el._fullLayout?.yaxis?.range;
    if (xRange && yRange) {
      const xCenter = (xRange[0] + xRange[1]) / 2;
      const yCenter = (yRange[0] + yRange[1]) / 2;
      const xSpan = (xRange[1] - xRange[0]) * 0.75;
      const ySpan = (yRange[1] - yRange[0]) * 0.75;
      relayout(ref, {
        "xaxis.range": [xCenter - xSpan, xCenter + xSpan],
        "yaxis.range": [yCenter - ySpan, yCenter + ySpan],
      });
    }
  };

  const handleReset = (ref) => {
    relayout(ref, {
      "xaxis.autorange": true,
      "yaxis.autorange": true,
    });
  };

  const handleDownload = (ref) => {
    const el = ref?.current?.el;
    const Plotly = getPlotly(ref);
    if (el && Plotly) {
      Plotly.downloadImage(el, {
        format: "svg",
        filename: "dashai-plot",
        height: 800,
        width: 1200,
        scale: 1,
      });
    }
  };

  const plotConfig = {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
  };

  const plotLayout = {
    ...plotData.layout,
    paper_bgcolor: plotData.layout?.paper_bgcolor || "white",
    plot_bgcolor: plotData.layout?.plot_bgcolor || "white",
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

  const iconBtnSx = {
    bgcolor: "rgba(255,255,255,0.85)",
    border: "1px solid rgba(0,0,0,0.08)",
    color: "#9e9e9e",
    width: 30,
    height: 30,
    "&:hover": {
      bgcolor: "rgba(255,255,255,1)",
      color: "#616161",
    },
  };

  const downloadBtnSx = {
    bgcolor: "#ef9f27",
    color: "white",
    width: 30,
    height: 30,
    "&:hover": {
      bgcolor: "#f5b94a",
    },
  };

  const ToolbarButtons = ({
    plotRefProp,
    showFullscreenExit = false,
    compact = false,
  }) => (
    <Box
      sx={{
        position: "absolute",
        top: 8,
        right: 8,
        zIndex: 2,
        display: "flex",
        alignItems: "center",
        gap: 0.5,
      }}
    >
      {!compact && (
        <>
          <Tooltip title="Zoom in" arrow>
            <IconButton
              size="small"
              onClick={() => handleZoomIn(plotRefProp)}
              sx={iconBtnSx}
            >
              <ZoomInIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title="Zoom out" arrow>
            <IconButton
              size="small"
              onClick={() => handleZoomOut(plotRefProp)}
              sx={iconBtnSx}
            >
              <ZoomOutIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title="Reset axes" arrow>
            <IconButton
              size="small"
              onClick={() => handleReset(plotRefProp)}
              sx={iconBtnSx}
            >
              <RestartAltIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Tooltip>
        </>
      )}
      {showFullscreenExit ? (
        <Tooltip title="Exit fullscreen" arrow>
          <IconButton
            size="small"
            onClick={() => setExpanded(false)}
            sx={iconBtnSx}
          >
            <FullscreenExitIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
      ) : (
        <Tooltip title="Fullscreen" arrow>
          <IconButton
            size="small"
            onClick={() => setExpanded(true)}
            sx={iconBtnSx}
          >
            <FullscreenIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
      )}
      <Tooltip title="Download as SVG" arrow>
        <IconButton
          size="small"
          onClick={() => handleDownload(plotRefProp)}
          sx={downloadBtnSx}
        >
          <FileDownloadOutlinedIcon sx={{ fontSize: 18 }} />
        </IconButton>
      </Tooltip>
    </Box>
  );

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
        <ToolbarButtons plotRefProp={plotRef} compact={minimalist} />
        {!expanded ? (
          <Plot
            ref={plotRef}
            id="plotly-graph"
            data={plotData.data}
            layout={plotLayout}
            style={{
              width: "100%",
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
            <Box sx={{ position: "relative", width: "100%", height: "100%" }}>
              <ToolbarButtons
                plotRefProp={fullscreenPlotRef}
                showFullscreenExit
              />
              <Plot
                ref={fullscreenPlotRef}
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
                config={{ ...plotConfig, scrollZoom: true }}
              />
            </Box>
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
