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
 * Append one run's bar trace to graphsToView.
 *
 * @param {object}  graphsToView  Accumulator object { bar: [] }
 * @param {object}  run           Run data object
 * @param {string[]} metrics      Metric names to plot
 * @param {number[]} values       Corresponding metric values (null if missing)
 * @param {number}  runIndex      Zero-based index used to pick a trace color
 * @param {object}  theme         MUI theme object
 */
function graphsMaking(graphsToView, run, metrics, values, runIndex, theme) {
  graphsToView.bar = graphsToView.bar || [];

  const colors = getTraceColors(theme);
  const color = colors[runIndex % colors.length];
  const runLabel = run.run_name || run.name || `Run ${runIndex + 1}`;

  graphsToView.bar.push({
    type: "bar",
    name: runLabel,
    x: metrics,
    y: values,
    marker: { color, opacity: 0.85 },
  });

  return graphsToView;
}

/**
 * Build a single Plotly heatmap trace from all runs at once.
 *
 * Each metric column is independently min-max normalized relative to the
 * visible runs, so every metric fills the full color range regardless of its
 * scale. For lower-is-better metrics (maximize=false in metricsMetadata), the
 * normalization is inverted so the lowest raw value maps to the "best" color.
 *
 * Colorscale: orange (primary) = worst → green (secondary) = best.
 *
 * @param {object[]} finishedRuns          Array of completed run objects
 * @param {string[]} metrics               Metric names (x-axis columns)
 * @param {string}   metricsKey            e.g. "test_metrics"
 * @param {object}   theme                 MUI theme object
 * @param {object}   [metricsMetadata={}]  { MetricName: { maximize: bool } }
 * @returns {object[]}  Array containing one heatmap trace
 */
function heatmapMaking(
  finishedRuns,
  metrics,
  metricsKey,
  theme,
  metricsMetadata = {},
) {
  const MAX_LABEL = 20;
  const truncate = (s) =>
    s.length > MAX_LABEL ? `${s.slice(0, MAX_LABEL)}…` : s;

  const runLabels = finishedRuns.map((run, idx) =>
    truncate(run.run_name || run.name || `Run ${idx + 1}`),
  );

  // Raw values matrix [runs × metrics]
  const zRaw = finishedRuns.map((run) => {
    const metricsObj = run[metricsKey] ?? {};
    return metrics.map((m) => {
      const v = metricsObj[m];
      if (v === undefined || v === null) return null;
      if (Array.isArray(v)) return v[v.length - 1]?.value ?? null;
      return typeof v === "number" ? v : null;
    });
  });

  // Per-column min-max normalization.
  // Lower-is-better metrics (maximize===false) are inverted so the best
  // (lowest) value maps to 1 (green) and the worst maps to 0 (orange).
  const zColorByCol = metrics.map((m, mIdx) => {
    const colVals = zRaw.map((row) => row[mIdx]).filter((v) => v !== null);
    const colMin = colVals.length ? Math.min(...colVals) : 0;
    const colMax = colVals.length ? Math.max(...colVals) : 1;
    const range = colMax - colMin;
    const isInverse = metricsMetadata[m]?.maximize === false;
    return zRaw.map((row) => {
      const v = row[mIdx];
      if (v === null) return null;
      const norm = range === 0 ? 0.5 : (v - colMin) / range;
      return isInverse ? 1 - norm : norm;
    });
  });
  // Transpose back to [runs × metrics]
  const zNorm = finishedRuns.map((_, rIdx) =>
    metrics.map((_, mIdx) => zColorByCol[mIdx][rIdx]),
  );

  const annotationText = zRaw.map((row) =>
    row.map((v) => (v !== null ? v.toFixed(4) : "N/A")),
  );

  // X-axis labels: add ↓ arrow for lower-is-better metrics
  const xLabels = metrics.map((m) =>
    metricsMetadata[m]?.maximize === false ? `${m} ↓` : m,
  );

  const primaryColor = theme.palette.primary.main;
  const secondaryColor = theme.palette.secondary.main;

  return [
    {
      type: "heatmap",
      x: xLabels,
      y: runLabels,
      z: zNorm,
      text: annotationText,
      texttemplate: "%{text}",
      textfont: { size: 11, weight: 700, color: theme.palette.text.primary },
      // orange (primary) = min/worst, green (secondary) = max/best
      colorscale: [
        [0, primaryColor],
        [1, secondaryColor],
      ],
      zauto: false,
      zmin: 0,
      zmax: 1,
      showscale: true,
      colorbar: {
        tickmode: "array",
        tickvals: [0, 1],
        ticktext: ["Worst", "Best"],
        tickfont: { color: theme.palette.text.primary },
      },
      hoverongaps: false,
      xgap: 2,
      ygap: 2,
    },
  ];
}

export { heatmapMaking };
export default graphsMaking;
