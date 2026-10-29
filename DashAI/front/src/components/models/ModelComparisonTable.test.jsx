/**
 * The session comparison table: one column per metric a run reports on the
 * chosen split, a direction arrow from the metric's `maximize` metadata, and a
 * star on the best value of each column.
 */

import React from "react";
import { screen, within } from "@testing-library/react";

jest.mock("./ModelsContext", () => ({
  useModels: jest.fn(),
}));

jest.mock("../../hooks/useStrategyKind", () => ({
  useStrategyKind: () => null,
}));

jest.mock("../credentials/credentialStatus", () => ({
  useCredentialStatuses: () => ({ statuses: {}, loaded: true }),
  getComponentCredentialState: () => ({ locked: false, requiredPlatforms: "" }),
}));

import { useModels } from "./ModelsContext";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ModelComparisonTable from "./ModelComparisonTable";

const METRICS = [
  { name: "Accuracy", description: "Accuracy", metadata: { maximize: true } },
  {
    name: "MAE",
    description: "Mean absolute error",
    metadata: { maximize: false },
  },
  // A metric with no direction: no arrow, no star.
  { name: "Custom", description: "Custom", metadata: {} },
];

const FINISHED = 3;

const RUNS = [
  {
    id: 1,
    name: "run_a",
    model_name: "ModelA",
    status: FINISHED,
    test_metrics: { Accuracy: 0.9, MAE: 0.3, Custom: 5 },
    validation_metrics: { Accuracy: 0.7, MAE: 0.1 },
  },
  {
    id: 2,
    name: "run_b",
    model_name: "ModelB",
    status: FINISHED,
    test_metrics: { Accuracy: 0.8, MAE: 0.2 },
    validation_metrics: { Accuracy: 0.75, MAE: 0.4 },
    validation_metrics_std: { Accuracy: 0.01 },
  },
  {
    id: 3,
    name: "run_c",
    model_name: "ModelC",
    status: FINISHED,
    test_metrics: { Accuracy: 0.85 },
    validation_metrics: { Accuracy: 0.6, MAE: 0.5 },
  },
];

function renderTable(props = {}) {
  useModels.mockReturnValue({
    allModels: [],
    allMetrics: METRICS,
    selectedSession: null,
  });
  return renderWithProviders(
    <ModelComparisonTable
      runs={RUNS}
      onTrain={jest.fn()}
      onViewDetails={jest.fn()}
      onDelete={jest.fn()}
      {...props}
    />,
  );
}

const headers = () =>
  screen
    .getAllByRole("columnheader")
    .map((th) => th.querySelector(".Mui-TableHeadCell-Content-Wrapper"))
    .map((el) => (el ? el.textContent.trim() : ""));

// { runName: [cellText, ...] } in header order.
const rowsByRun = () => {
  const out = {};
  screen
    .getAllByRole("row")
    .slice(1)
    .forEach((tr) => {
      const cells = within(tr)
        .getAllByRole("cell")
        .map((td) => td.textContent.trim());
      out[cells[0]] = cells;
    });
  return out;
};

const cellOf = (runName, header) => {
  const index = headers().indexOf(header);
  if (index === -1) throw new Error(`no column ${header} in ${headers()}`);
  return rowsByRun()[runName][index];
};

describe("ModelComparisonTable", () => {
  test("test split: one column per metric reported, with direction arrows", () => {
    renderTable();

    expect(headers()).toEqual([
      "Model Name",
      "Model",
      "Accuracy↑",
      "MAE↓",
      "Custom",
      "Actions",
    ]);
  });

  test("test split: the best value of each directed metric gets the star", () => {
    renderTable();

    // Accuracy maximizes: run_a (0.9) is best.
    expect(cellOf("run_a", "Accuracy↑")).toBe("★0.9000");
    expect(cellOf("run_b", "Accuracy↑")).toBe("0.8000");
    expect(cellOf("run_c", "Accuracy↑")).toBe("0.8500");

    // MAE minimizes: run_b (0.2) is best; run_c has no value.
    expect(cellOf("run_a", "MAE↓")).toBe("0.3000");
    expect(cellOf("run_b", "MAE↓")).toBe("★0.2000");
    expect(cellOf("run_c", "MAE↓")).toBe("-");

    // No direction: never starred, missing values read "-".
    expect(cellOf("run_a", "Custom")).toBe("5.0000");
    expect(cellOf("run_b", "Custom")).toBe("-");
    expect(cellOf("run_c", "Custom")).toBe("-");
  });

  test("validation split reads validation_metrics under the val prefix", () => {
    renderTable({ metricSplit: "validation" });

    // The "val_" prefix is stripped back to the bare metric name, so headers
    // and metadata lookups match; Custom is absent from validation_metrics.
    expect(headers()).toEqual([
      "Model Name",
      "Model",
      "Accuracy↑",
      "MAE↓",
      "Actions",
    ]);

    // Accuracy maximizes: run_b (0.75) best, and carries its std.
    expect(cellOf("run_a", "Accuracy↑")).toBe("0.7000");
    expect(cellOf("run_b", "Accuracy↑")).toBe("★0.7500±0.0100");
    expect(cellOf("run_c", "Accuracy↑")).toBe("0.6000");

    // MAE minimizes: run_a (0.1) best.
    expect(cellOf("run_a", "MAE↓")).toBe("★0.1000");
    expect(cellOf("run_b", "MAE↓")).toBe("0.4000");
    expect(cellOf("run_c", "MAE↓")).toBe("0.5000");
  });

  test("a split no run reports yields no metric column", () => {
    renderTable({ metricSplit: "train" });

    expect(headers()).toEqual(["Model Name", "Model", "Actions"]);
  });

  test("a running run shows '-' but its value still decides the star", () => {
    useModels.mockReturnValue({
      allModels: [],
      allMetrics: METRICS,
      selectedSession: null,
    });
    const runs = [
      RUNS[0],
      // Running (status 2) with the better Accuracy: still sets the best value,
      // so run_a loses its star while the running row shows "-".
      { ...RUNS[1], status: 2, test_metrics: { Accuracy: 0.99 } },
    ];
    renderWithProviders(
      <ModelComparisonTable
        runs={runs}
        onTrain={jest.fn()}
        onViewDetails={jest.fn()}
        onDelete={jest.fn()}
      />,
    );

    expect(cellOf("run_a", "Accuracy↑")).toBe("0.9000");
    expect(cellOf("run_b", "Accuracy↑")).toBe("-");
  });
});
