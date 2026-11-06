import { metricSummary } from "./metricSummary";

/*
 * The final value of each metric a run reports on a split, which the run's
 * live metrics tab shows above its charts.
 */

describe("metricSummary", () => {
  it("the final value of each metric, a per-step history read at its end", () => {
    const run = {
      validation_metrics: { MAE: 0.25, Loss: [{ value: 3 }, { value: 2 }] },
    };

    expect(metricSummary(run, "validation")).toEqual([
      { name: "MAE", value: 0.25, reason: null },
      { name: "Loss", value: 2, reason: null },
    ]);
  });

  it("drops a value that is not a number", () => {
    expect(metricSummary({ test_metrics: { F1: "n/a" } }, "test")).toEqual([]);
  });

  it("a metric the run could not compute keeps its place, with the reason", () => {
    const reason =
      "MAPE divides by each actual value, and it is zero on 1 row.";
    const run = {
      test_metrics: { MAE: 0.3 },
      test_metrics_unavailable: { MAPE: reason },
    };

    expect(metricSummary(run, "test")).toEqual([
      { name: "MAE", value: 0.3, reason: null },
      { name: "MAPE", value: null, reason },
    ]);
  });

  it("nothing on a split the run reports nothing for", () => {
    expect(metricSummary({}, "train")).toEqual([]);
  });
});
