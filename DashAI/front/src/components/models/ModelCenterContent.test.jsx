/**
 * The task selection grid of the models module: each task card's icon is the
 * one the task declares in `metadata.icon` (the default icon when it declares
 * none, or one Material UI does not have), and its badge comes from
 * `metadata.requires_target`.
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
    metadata: { requires_target: true, icon: "TableChart" },
  },
  {
    name: "RegressionTask",
    display_name: "Regression",
    metadata: { icon: "ShowChart" },
  },
  {
    name: "TranslationTask",
    display_name: "Translation",
    metadata: { requires_target: true, icon: "Translate" },
  },
  {
    name: "ClassificationTask",
    display_name: "Classification",
    metadata: { requires_target: true, icon: "NoSuchIcon" },
  },
  {
    name: "PluginTask",
    display_name: "Plugin",
    metadata: { requires_target: false, icon: "Timeline" },
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
  test("the icon the task declares, the default otherwise", () => {
    renderGrid();

    expect(iconOf("Tabular Classification")).toEqual(["TableChartIcon"]);
    expect(iconOf("Regression")).toEqual(["ShowChartIcon"]);
    expect(iconOf("Translation")).toEqual(["TranslateIcon"]);
    // A task the frontend never heard of draws the icon it declares.
    expect(iconOf("Plugin")).toEqual(["TimelineIcon"]);
    // An icon Material UI does not have, or none at all.
    expect(iconOf("Classification")).toEqual(["ScienceIcon"]);
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
    renderGrid([
      { name: "TextClassificationTask", metadata: { icon: "TextFields" } },
    ]);

    expect(iconOf("Text Classification")).toEqual(["TextFieldsIcon"]);
  });
});
