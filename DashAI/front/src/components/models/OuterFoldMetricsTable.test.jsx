import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import { getOuterAveragedMetrics } from "../../api/run";
import OuterFoldMetricsTable from "./OuterFoldMetricsTable";

jest.mock("../../api/run", () => ({ getOuterAveragedMetrics: jest.fn() }));

/*
 * The averaged metrics of a nested run's outer folds, one row per metric.
 */

describe("OuterFoldMetricsTable", () => {
  it("one row per metric, with the mean and the deviation", async () => {
    getOuterAveragedMetrics.mockResolvedValue({
      train_metrics: { MAE: 0.1 },
      train_metrics_std: { MAE: 0.01 },
      validation_metrics: { MAE: 0.2 },
    });
    renderWithProviders(<OuterFoldMetricsTable run={{ id: 1 }} />);

    expect(await screen.findByText("MAE")).toBeInTheDocument();
    expect(screen.getByText("0.1000 ± 0.0100")).toBeInTheDocument();
    expect(screen.getByText("0.2000")).toBeInTheDocument();
  });

  it("a metric the run could not compute keeps its row, with the reason", async () => {
    const reason =
      "MAPE divides by each actual value, and it is zero on 1 row.";
    getOuterAveragedMetrics.mockResolvedValue({
      train_metrics: { MAE: 0.1 },
      validation_metrics: { MAE: 0.2 },
      validation_metrics_unavailable: { MAPE: reason },
    });
    renderWithProviders(<OuterFoldMetricsTable run={{ id: 1 }} />);

    expect(await screen.findByText("MAPE")).toBeInTheDocument();
    expect(screen.getByLabelText(reason)).toHaveTextContent("—");
  });
});
