/**
 * The goal-metric selector lists the metrics compatible with the task in the
 * order the backend returns them, and with autoSelectDefault picks the first.
 */

import React from "react";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

jest.mock("../../../hooks/useMetricByTask", () => ({
  __esModule: true,
  default: jest.fn(),
}));

import useMetricsByTask from "../../../hooks/useMetricByTask";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import ModelsTableSelectMetric from "./ModelsTableSelectMetric";

// Deliberately not alphabetical: the order is the hook's, untouched.
const METRICS = [
  { name: "F1", metadata: { maximize: true } },
  { name: "Accuracy", metadata: { maximize: true } },
  { name: "LogLoss", metadata: { maximize: false } },
];

const loaded = (compatibleMetrics = METRICS) =>
  useMetricsByTask.mockReturnValue({
    compatibleMetrics,
    loading: false,
    error: null,
  });

const select = () => screen.getByRole("combobox");

const options = async () => {
  userEvent.click(select());
  const listbox = await screen.findByRole("listbox");
  return within(listbox)
    .getAllByRole("option")
    .map((o) => o.textContent);
};

describe("ModelsTableSelectMetric", () => {
  beforeEach(() => jest.clearAllMocks());

  test("asks the hook for the task's metrics", () => {
    loaded();
    renderWithProviders(
      <ModelsTableSelectMetric
        taskName="TabularClassificationTask"
        handleSelectedMetric={jest.fn()}
      />,
    );
    expect(useMetricsByTask).toHaveBeenCalledWith({
      taskName: "TabularClassificationTask",
    });
  });

  test("lists the metrics in the order the hook returns them", async () => {
    loaded();
    renderWithProviders(
      <ModelsTableSelectMetric taskName="T" handleSelectedMetric={jest.fn()} />,
    );
    expect(await options()).toEqual(["F1", "Accuracy", "LogLoss"]);
  });

  test("autoSelectDefault picks the first metric listed", async () => {
    loaded();
    const handleSelectedMetric = jest.fn();
    renderWithProviders(
      <ModelsTableSelectMetric
        taskName="T"
        handleSelectedMetric={handleSelectedMetric}
        autoSelectDefault
      />,
    );
    await waitFor(() =>
      expect(handleSelectedMetric).toHaveBeenCalledWith("F1"),
    );
    expect(handleSelectedMetric).toHaveBeenCalledTimes(1);
    expect(select()).toHaveTextContent("F1");
  });

  test("without autoSelectDefault nothing is selected", () => {
    loaded();
    const handleSelectedMetric = jest.fn();
    renderWithProviders(
      <ModelsTableSelectMetric
        taskName="T"
        handleSelectedMetric={handleSelectedMetric}
        required
      />,
    );
    expect(handleSelectedMetric).not.toHaveBeenCalled();
    expect(document.querySelector("input").value).toBe("");
    // Required and empty once loaded reads as an error.
    expect(document.querySelector(".MuiInputBase-root")).toHaveClass(
      "Mui-error",
    );
  });

  test("a saved metric wins over the default", () => {
    loaded();
    const handleSelectedMetric = jest.fn();
    renderWithProviders(
      <ModelsTableSelectMetric
        taskName="T"
        metricName="LogLoss"
        handleSelectedMetric={handleSelectedMetric}
        autoSelectDefault
      />,
    );
    expect(handleSelectedMetric).not.toHaveBeenCalled();
    expect(select()).toHaveTextContent("LogLoss");
  });

  test("no default is picked while the list is still loading", () => {
    useMetricsByTask.mockReturnValue({
      compatibleMetrics: METRICS,
      loading: true,
      error: null,
    });
    const handleSelectedMetric = jest.fn();
    renderWithProviders(
      <ModelsTableSelectMetric
        taskName="T"
        handleSelectedMetric={handleSelectedMetric}
        autoSelectDefault
      />,
    );
    expect(handleSelectedMetric).not.toHaveBeenCalled();
  });

  test("choosing an option reports it", async () => {
    loaded();
    const handleSelectedMetric = jest.fn();
    renderWithProviders(
      <ModelsTableSelectMetric
        taskName="T"
        handleSelectedMetric={handleSelectedMetric}
      />,
    );
    userEvent.click(select());
    userEvent.click(await screen.findByRole("option", { name: "LogLoss" }));
    expect(handleSelectedMetric).toHaveBeenCalledWith("LogLoss");
  });
});
