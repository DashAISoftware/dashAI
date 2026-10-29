/**
 * The task selection grid of the models module: each task card's icon comes
 * from a map keyed by the task's name (anything else gets the default icon),
 * and its badge from `metadata.requires_target`.
 */

import React from "react";
import { screen, within } from "@testing-library/react";

jest.mock("./ModelsContext", () => ({
  useModels: jest.fn(),
}));

jest.mock("../tour/TourProvider", () => ({
  useTourContext: () => null,
}));

// Rendered only past the task step; kept out of the module graph.
jest.mock("./CreateSessionSteps", () => () => null);
jest.mock("../DatasetVisualization", () => () => null);
jest.mock("./ModelsBreadcrumbs", () => () => null);

import { useModels } from "./ModelsContext";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ModelsCenterContent from "./ModelCenterContent";

beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

afterAll(() => {
  delete global.ResizeObserver;
});

const TASKS = [
  {
    name: "TabularClassificationTask",
    display_name: "Tabular Classification",
    metadata: { requires_target: true },
  },
  {
    name: "RegressionTask",
    display_name: "Regression",
    metadata: {},
  },
  {
    name: "TranslationTask",
    display_name: "Translation",
    metadata: { requires_target: true },
  },
  {
    name: "ClassificationTask",
    display_name: "Classification",
    metadata: { requires_target: true },
  },
  {
    name: "PluginTask",
    display_name: "Plugin",
    metadata: { requires_target: false },
  },
  // No display name: derived from the class name.
  { name: "ClusteringTask", metadata: { requires_target: false } },
];

const renderGrid = (tasks = TASKS) => {
  useModels.mockReturnValue({
    sessions: [],
    setSessions: jest.fn(),
    selectedTask: null,
    tasks,
    loadingTasks: false,
    datasets: [{ id: 1, name: "ds" }],
    selectedDatasetId: null,
    step: 0,
  });
  renderWithProviders(<ModelsCenterContent />);
};

const card = (displayName) => screen.getByText(displayName).closest("button");

const iconOf = (displayName) =>
  Array.from(card(displayName).querySelectorAll("svg[data-testid]")).map(
    (svg) => svg.getAttribute("data-testid"),
  );

describe("ModelsCenterContent task grid", () => {
  test("icon per task name, default for names not in the map", () => {
    renderGrid();

    expect(iconOf("Tabular Classification")).toEqual(["TableChartIcon"]);
    expect(iconOf("Regression")).toEqual(["ShowChartIcon"]);
    expect(iconOf("Translation")).toEqual(["TranslateIcon"]);
    expect(iconOf("Classification")).toEqual(["CategoryIcon"]);
    expect(iconOf("Plugin")).toEqual(["ScienceIcon"]);
    expect(iconOf("Clustering")).toEqual(["ScienceIcon"]);
  });

  test("badge: unsupervised only when requires_target is false", () => {
    renderGrid();

    const badge = (name) =>
      within(card(name)).queryByText(/^(Supervised|Unsupervised)$/)
        ?.textContent;
    expect(badge("Tabular Classification")).toBe("Supervised");
    expect(badge("Translation")).toBe("Supervised");
    // Missing metadata reads as supervised.
    expect(badge("Regression")).toBe("Supervised");
    expect(badge("Plugin")).toBe("Unsupervised");
    expect(badge("Clustering")).toBe("Unsupervised");
  });

  test("a task without display_name is labeled from its class name", () => {
    renderGrid([{ name: "TextClassificationTask", metadata: {} }]);

    expect(iconOf("Text Classification")).toEqual(["TextFieldsIcon"]);
  });
});
