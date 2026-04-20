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
 * Colour mapping uses the backend-provided bounded/maximize metadata:
 *  - bounded=true  + maximize=true  → z = raw value (≥0 → gradient; <0 → black)
 *  - bounded=true  + maximize=false → z = 1 − raw value (↓ label on x-axis)
 *  - bounded=false or missing meta  → z = null (no colour; hover shows "Not bounded")
 *
 * A sentinel z value of -0.01 (below zmin=0) is used to render
 * bounded+maximize metrics with negative raw values as black cells,
 * signalling "worse than chance / broken model".
 *
 * @param {object[]} finishedRuns          Array of completed run objects
 * @param {string[]} metrics               Metric names (x-axis columns)
 * @param {string}   metricsKey            e.g. "test_metrics"
 * @param {object}   theme                 MUI theme object
 * @param {object}   [metricsMetadata={}]  { MetricName: { bounded, maximize } }
 * @returns {object[]}  Array containing one heatmap trace
 */
function heatmapMaking(
  finishedRuns,
  metrics,
  metricsKey,
  theme,
  metricsMetadata = {},
) {
  // Any bounded+maximize metric whose raw value is negative gets this sentinel,
  // which maps to near-black via the colorscale (e.g. CohenKappa < 0).
  const SENTINEL = -0.01;
  const ZMIN = SENTINEL;
  const ZMAX = 1.0;
  // Proportional position of z=0 inside [ZMIN, ZMAX] — used to place the
  // sharp black→background boundary in the colorscale.
  const pZero = (0 - ZMIN) / (ZMAX - ZMIN); // ≈ 0.0099

  const runLabels = finishedRuns.map(
    (run, idx) => run.run_name || run.name || `Run ${idx + 1}`,
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

  // X-axis labels:
  //   bounded + maximize=false → append ↓ (scale is inverted: lower raw = brighter)
  //   everything else          → plain metric name
  const xLabels = metrics.map((m) => {
    const meta = metricsMetadata[m];
    return meta && meta.bounded && !meta.maximize ? `${m} ↓` : m;
  });

  // Colour z-matrix (absolute scale [ZMIN, ZMAX]):
  //   unbounded            → null  (transparent gap, hover shows "Not bounded")
  //   bounded + maximize   → raw value, or SENTINEL when raw < 0 (renders black)
  //   bounded + !maximize  → 1 − raw  (inverted so brighter = better)
  const zColor = zRaw.map((row) =>
    row.map((v, mIdx) => {
      if (v === null) return null;
      const meta = metricsMetadata[metrics[mIdx]];
      if (!meta || !meta.bounded) return null;
      if (meta.maximize) return v < 0 ? SENTINEL : v;
      return 1 - v;
    }),
  );

  // Text annotations: always show the real raw value (including negatives).
  const annotationText = zRaw.map((row) =>
    row.map((v) => (v !== null ? v.toFixed(4) : "N/A")),
  );

  // Hover content: "Not bounded" for unbounded columns, raw value otherwise.
  // Combined with hoverongaps: true this surfaces info even on null-z cells.
  const customData = zRaw.map((row) =>
    row.map((v, mIdx) => {
      const meta = metricsMetadata[metrics[mIdx]];
      if (!meta || !meta.bounded) return "Not bounded";
      return v !== null ? v.toFixed(4) : "N/A";
    }),
  );

  const bgColor = theme.palette.background.paper;
  const primaryColor = theme.palette.primary.main;

  return [
    {
      type: "heatmap",
      x: xLabels,
      y: runLabels,
      z: zColor,
      text: annotationText,
      texttemplate: "%{text}",
      customdata: customData,
      hovertemplate: "<b>%{x}</b><br>%{y}<br>%{customdata}<extra></extra>",
      colorscale: [
        [0, "#1a1a1a"], // SENTINEL region → near black
        [pZero * 0.99, "#1a1a1a"], // just below z=0 → still black
        [pZero, bgColor], // z=0 → background (sharp boundary)
        [1, primaryColor], // z=1 → primary colour
      ],
      zauto: false,
      zmin: ZMIN,
      zmax: ZMAX,
      showscale: true,
      colorbar: {
        tickmode: "array",
        tickvals: [0, 1],
        ticktext: ["0", "1"],
        tickfont: { color: theme.palette.text.primary },
      },
      hoverongaps: true,
      xgap: 2,
      ygap: 2,
    },
  ];
}

export { heatmapMaking };
export default graphsMaking;
