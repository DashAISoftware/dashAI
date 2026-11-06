import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import { getFoldMetrics } from "../../api/run";
import FoldMetricsChart from "./FoldMetricsChart";

jest.mock("react-plotly.js", () => () => null);
jest.mock("../../api/run", () => ({
  getFoldMetrics: jest.fn(),
  isRepeatedFoldMetrics: () => false,
}));
jest.mock("./ModelsContext", () => ({
  useModels: () => ({ selectedSession: null }),
}));
jest.mock("../../hooks/useStrategyKind", () => ({
  useStrategyMetadata: () => null,
}));

/*
 * The per-fold chart of a run. A backtest offers it too, one score per
 * origin, so a run without fold scores is said in the backend's words, not
 * blamed on cross-validation.
 */

describe("FoldMetricsChart", () => {
  it("a run without fold scores says what the backend said, and only that", async () => {
    const detail = "Run 4 has no fold metric with a value.";
    getFoldMetrics.mockRejectedValue({
      name: "AxiosError",
      response: { status: 404, data: { detail } },
    });

    renderWithProviders(<FoldMetricsChart run={{ id: 4, nested: false }} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(detail);
    expect(alert).not.toHaveTextContent(/cross-validation/i);
  });
});
