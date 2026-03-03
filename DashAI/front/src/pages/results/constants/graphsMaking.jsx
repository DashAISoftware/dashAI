const getTraceColors = (theme) => [
  theme.palette.primary.main,
  theme.palette.secondary.main,
  theme.palette.chart?.train || "#4caf50",
  theme.palette.chart?.test || "#2196f3",
  theme.palette.chart?.validation || "#ff9800",
  theme.palette.success?.main || "#43A047",
  theme.palette.info?.main || "#2196f3",
  theme.palette.warning?.main || "#ed6c02",
  theme.palette.error?.main || "#d32f2f",
];

/**
 * Append one run's traces to graphsToView for radar and bar chart types.
 *
 * @param {object}  graphsToView  Accumulator object { radar: [], bar: [] }
 * @param {object}  run           Run data object
 * @param {string[]} metrics      Metric names to plot
 * @param {number[]} values       Corresponding metric values (null if missing)
 * @param {number}  runIndex      Zero-based index used to pick a trace color
 * @param {object}  theme         MUI theme object
 */
function graphsMaking(graphsToView, run, metrics, values, runIndex, theme) {
  graphsToView.radar = graphsToView.radar || [];
  graphsToView.bar = graphsToView.bar || [];

  const colors = getTraceColors(theme);
  const color = colors[runIndex % colors.length];
  const runLabel = run.run_name || run.name || `Run ${runIndex + 1}`;

  const radarValues = values.map((v) => v ?? 0);
  graphsToView.radar.push({
    type: "scatterpolar",
    name: runLabel,
    r: [...radarValues, radarValues[0]],
    theta: [...metrics, metrics[0]],
    fill: "toself",
    line: { color, width: 2 },
    opacity: 0.85,
  });

  graphsToView.bar.push({
    type: "bar",
    name: runLabel,
    x: metrics,
    y: values,
    marker: { color, opacity: 0.85 },
  });

  return graphsToView;
}

export default graphsMaking;
