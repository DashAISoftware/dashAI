import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import { getRunForecasts } from "../../api/run";
import ForecastsChart from "./ForecastsChart";

let mockPlotProps = null;
jest.mock("react-plotly.js", () => (props) => {
  mockPlotProps = props;
  return <div data-testid="plot" />;
});
jest.mock("../../api/run", () => ({ getRunForecasts: jest.fn() }));

/*
 * The forecasts tab of a backtest run: what GET /run/{id}/forecasts saved,
 * drawn origin by origin, the actual values against the forecast and its
 * intervals by date. Nothing is computed on the values.
 */

const DATES = ["2023-04-01T00:00:00", "2023-05-01T00:00:00"];
const FORECASTS = {
  version: 1,
  freq: "MS",
  horizon: 2,
  levels: [80, 95],
  origins: [
    {
      partition: "validation",
      index: 0,
      origin_step: 40,
      dates: ["2023-02-01T00:00:00", "2023-03-01T00:00:00"],
      actual: [10, 11],
      forecast: [9.5, 10.5],
      lower: { 80: [9, 10], 95: [8, 9] },
      upper: { 80: [10, 11], 95: [11, 12] },
    },
    {
      partition: "test",
      index: 0,
      origin_step: 42,
      dates: DATES,
      actual: [12, null],
      forecast: [11.5, 12.5],
      lower: { 80: [11, 12], 95: [10, 11] },
      upper: { 80: [12, 13], 95: [13, 14] },
    },
  ],
};

const traces = () => mockPlotProps.data.map((trace) => trace.name);

beforeEach(() => {
  mockPlotProps = null;
  getRunForecasts.mockReset();
});

describe("ForecastsChart", () => {
  it("asks for the run's forecasts and draws the first origin", async () => {
    getRunForecasts.mockResolvedValue(FORECASTS);
    renderWithProviders(<ForecastsChart run={{ id: 7 }} />);

    await screen.findByTestId("plot");
    expect(getRunForecasts).toHaveBeenCalledWith(7);
    const byName = Object.fromEntries(
      mockPlotProps.data.map((trace) => [trace.name, trace]),
    );
    expect(byName.Actual.x).toEqual(FORECASTS.origins[0].dates);
    expect(byName.Actual.y).toEqual([10, 11]);
    expect(byName.Forecast.y).toEqual([9.5, 10.5]);
  });

  it("draws one band per level the file carries, widest first", async () => {
    getRunForecasts.mockResolvedValue(FORECASTS);
    renderWithProviders(<ForecastsChart run={{ id: 7 }} />);
    await screen.findByTestId("plot");

    expect(traces()).toEqual([
      "95% interval",
      "95% interval",
      "80% interval",
      "80% interval",
      "Actual",
      "Forecast",
    ]);
    const [upper95, lower95] = mockPlotProps.data;
    expect(upper95.y).toEqual([11, 12]);
    expect(lower95.y).toEqual([8, 9]);
    expect(lower95.fill).toBe("tonexty");
  });

  it("offers every origin by its partition, and draws the one chosen", async () => {
    getRunForecasts.mockResolvedValue(FORECASTS);
    renderWithProviders(<ForecastsChart run={{ id: 7 }} />);
    await screen.findByTestId("plot");

    fireEvent.click(screen.getByRole("button", { name: "Test" }));

    await waitFor(() =>
      expect(mockPlotProps.data.find((t) => t.name === "Actual").x).toEqual(
        DATES,
      ),
    );
    expect(mockPlotProps.data.find((t) => t.name === "Actual").y).toEqual([
      12,
      null,
    ]);
    expect(
      screen.getByRole("button", { name: "Validation" }),
    ).toBeInTheDocument();
  });

  it("a model without intervals: no bands", async () => {
    getRunForecasts.mockResolvedValue({
      ...FORECASTS,
      levels: [],
      origins: FORECASTS.origins.map((origin) => ({
        ...origin,
        lower: {},
        upper: {},
      })),
    });
    renderWithProviders(<ForecastsChart run={{ id: 7 }} />);
    await screen.findByTestId("plot");

    expect(traces()).toEqual(["Actual", "Forecast"]);
  });

  it("a run without forecasts says what the backend said", async () => {
    const detail = "Run 7 has no forecasts.";
    getRunForecasts.mockRejectedValue({ response: { data: { detail } } });
    renderWithProviders(<ForecastsChart run={{ id: 7 }} />);

    expect(await screen.findByText(detail)).toBeInTheDocument();
  });
});
