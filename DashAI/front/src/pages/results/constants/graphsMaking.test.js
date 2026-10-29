/**
 * The plot data the session results charts are built from: the bar panels
 * (one per metric) and the all-runs heatmap. A metric whose metadata says
 * `maximize: false` is drawn as lower-is-better.
 */

import { heatmapMaking, smallMultiplesMaking } from "./graphsMaking";

const theme = (mode = "dark") => ({
  palette: {
    mode,
    primary: { main: "#primary", light: "#best" },
    secondary: { main: "#secondary" },
    error: { main: "#worst-dark" },
    text: { primary: "#text" },
    chart: {
      palette: ["#g", "#bl", "#o", "#p", "#r", "#t", "#br", "#bg"],
    },
  },
});

const RUNS = [
  { id: 1, name: "run_a", test_metrics: { Accuracy: 0.9, MAE: 0.3 } },
  { id: 2, name: "run_b", test_metrics: { Accuracy: 0.7, MAE: 0.1 } },
  // No MAE, and Accuracy as a per-step history: the last value is read.
  {
    id: 3,
    run_name: "run_c",
    test_metrics: { Accuracy: [{ value: 0.5 }, { value: 0.8 }] },
  },
];

const METADATA = {
  Accuracy: { maximize: true },
  MAE: { maximize: false },
};

const METRICS = ["Accuracy", "MAE"];

describe("heatmapMaking", () => {
  const [trace] = heatmapMaking(
    RUNS,
    new Set(),
    METRICS,
    "test_metrics",
    theme(),
    METADATA,
  );

  test("returns a single heatmap trace over every visible run", () => {
    expect(trace.type).toBe("heatmap");
    expect(trace.y).toEqual(["run_a", "run_b", "run_c"]);
  });

  test("a lower-is-better metric gets the down arrow on its column", () => {
    expect(trace.x).toEqual(["Accuracy", "MAE ↓"]);
  });

  test("missing values read N/A and stay out of the color matrix", () => {
    expect(trace.text).toEqual([
      ["0.9000", "0.3000"],
      ["0.7000", "0.1000"],
      ["0.8000", "N/A"],
    ]);
    expect(trace.z[2][1]).toBeNull();
  });

  test("colors are min-max per column, inverted when lower is better", () => {
    const z = trace.z.map((row) =>
      row.map((v) => (v === null ? v : +v.toFixed(6))),
    );
    expect(z).toEqual([
      // Accuracy (max is best): 0.9 -> 1, 0.7 -> 0, 0.8 -> 0.5
      // MAE (min is best): 0.1 -> 1, 0.3 -> 0
      [1, 0],
      [0, 1],
      [0.5, null],
    ]);
  });

  test("the color scale runs worst to best on a fixed 0..1 range", () => {
    expect(trace.colorscale).toEqual([
      [0, "#worst-dark"],
      [1, "#best"],
    ]);
    expect(trace).toMatchObject({ zauto: false, zmin: 0, zmax: 1 });
    expect(trace.colorbar.ticktext).toEqual(["Worst", "Best"]);
  });

  test("in light mode the worst color is the fixed red", () => {
    const [light] = heatmapMaking(
      RUNS,
      new Set(),
      METRICS,
      "test_metrics",
      theme("light"),
      METADATA,
    );
    expect(light.colorscale[0]).toEqual([0, "#ff8383"]);
  });

  test("a column with a single distinct value sits at the middle", () => {
    const [flat] = heatmapMaking(
      RUNS.slice(0, 1),
      new Set(),
      METRICS,
      "test_metrics",
      theme(),
      METADATA,
    );
    expect(flat.z).toEqual([[0.5, 0.5]]);
  });

  test("without metadata nothing is inverted nor arrowed", () => {
    const [plain] = heatmapMaking(
      RUNS,
      new Set(),
      METRICS,
      "test_metrics",
      theme(),
    );
    expect(plain.x).toEqual(["Accuracy", "MAE"]);
    expect(plain.z[1][1]).toBe(0);
    expect(plain.z[0][1]).toBe(1);
  });

  test("hidden runs are dropped and the scale recomputed without them", () => {
    const [partial] = heatmapMaking(
      RUNS,
      new Set([1]),
      METRICS,
      "test_metrics",
      theme(),
      METADATA,
    );
    expect(partial.y).toEqual(["run_b", "run_c"]);
    expect(
      partial.z.map((row) => row.map((v) => (v === null ? v : +v.toFixed(6)))),
    ).toEqual([
      [0, 0.5],
      [1, null],
    ]);
  });
});

describe("smallMultiplesMaking", () => {
  const { panels, legend, yaxis } = smallMultiplesMaking(
    RUNS,
    new Set([2]),
    METRICS,
    "test_metrics",
    theme(),
    METADATA,
  );

  test("one panel per metric; lower-is-better titles carry the arrow", () => {
    expect(panels.map((p) => [p.metric, p.title])).toEqual([
      ["Accuracy", "Accuracy"],
      ["MAE", "MAE ↓"],
    ]);
  });

  test("bars hold visible runs only, a missing value as null", () => {
    expect(panels[0].data[0]).toMatchObject({
      type: "bar",
      orientation: "h",
      y: [0, 1],
      x: [0.9, 0.8],
      customdata: ["run_a", "run_c"],
    });
    expect(panels[1].data[0].x).toEqual([0.3, null]);
  });

  test("bar values are raw: lower-is-better does not reorder or invert", () => {
    const { panels: all } = smallMultiplesMaking(
      RUNS,
      new Set(),
      ["MAE"],
      "test_metrics",
      theme(),
      METADATA,
    );
    expect(all[0].data[0].x).toEqual([0.3, 0.1, null]);
  });

  test("the legend keeps every run, hidden ones flagged, colors fixed by position", () => {
    expect(legend).toEqual([
      { id: 1, label: "run_a", color: "#primary", hidden: false },
      { id: 2, label: "run_b", color: "#o", hidden: true },
      { id: 3, label: "run_c", color: "#g", hidden: false },
    ]);
    expect(panels[0].data[0].marker.color).toEqual(["#primary", "#g"]);
    expect(yaxis).toEqual({ tickvals: [0, 1], ticktext: ["run_a", "run_c"] });
  });
});
