/**
 * Build a Plotly layout object that respects the current MUI theme.
 * Colors update automatically whenever the user switches between light / dark mode.
 *
 * @param {string} selectedChart  "radar" | "bar"
 * @param {object} _graphsToView  Unused – kept for API compatibility
 * @param {object} theme          MUI theme object
 * @returns {{ generalLayout: object }}
 */
function layoutMaking(selectedChart, _graphsToView, theme) {
  const bgColor = theme.palette.background.paper;
  const textColor = theme.palette.text.primary;
  const gridColor = theme.palette.divider;

  const axisConfig =
    selectedChart === "radar"
      ? {
          polar: {
            bgcolor: bgColor,
            radialaxis: {
              visible: true,
              gridcolor: gridColor,
              linecolor: gridColor,
              tickfont: { color: textColor },
            },
            angularaxis: {
              color: textColor,
              gridcolor: gridColor,
              linecolor: gridColor,
            },
          },
        }
      : {
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

  const generalLayout = {
    ...axisConfig,
    showlegend: true,
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
    margin: { l: 60, r: 30, t: 40, b: 80 },
  };

  return { generalLayout };
}

export default layoutMaking;
