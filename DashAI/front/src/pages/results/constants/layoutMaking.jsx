/**
 * Build a Plotly layout object that respects the current MUI theme.
 * Colors update automatically whenever the user switches between light / dark mode.
 *
 * @param {string} selectedChart  "heatmap" | "bar"
 * @param {object} _graphsToView  Unused – kept for API compatibility
 * @param {object} theme          MUI theme object
 * @returns {{ generalLayout: object }}
 */
function layoutMaking(selectedChart, _graphsToView, theme) {
  const bgColor = theme.palette.background.paper;
  const textColor = theme.palette.text.primary;
  const gridColor = theme.palette.divider;

  let axisConfig;

  if (selectedChart === "heatmap") {
    axisConfig = {
      xaxis: {
        tickangle: -35,
        automargin: true,
        tickfont: { color: textColor },
        gridcolor: gridColor,
      },
      yaxis: {
        automargin: true,
        tickfont: { color: textColor },
        gridcolor: gridColor,
      },
    };
  } else {
    // "bar"
    axisConfig = {
      barmode: "group",
      xaxis: {
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        tickfont: { color: textColor },
      },
      yaxis: {
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        tickfont: { color: textColor },
      },
    };
  }

  const generalLayout = {
    ...axisConfig,
    showlegend: selectedChart !== "heatmap",
    height: 460,
    autosize: true,
    paper_bgcolor: bgColor,
    plot_bgcolor: bgColor,
    font: {
      color: textColor,
      family: theme.typography.fontFamily,
      size: 12,
    },
    legend: {
      bgcolor: bgColor,
      bordercolor: gridColor,
      borderwidth: 1,
    },
    margin:
      selectedChart === "heatmap"
        ? { l: 160, r: 60, t: 40, b: 100 }
        : { l: 60, r: 30, t: 40, b: 80 },
  };

  return { generalLayout };
}

export default layoutMaking;
