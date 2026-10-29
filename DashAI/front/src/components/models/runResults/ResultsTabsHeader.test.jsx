/**
 * Which result tabs a finished run offers, by the session's evaluation
 * strategy kind. The cross validation row (fold graphs, nested results) is
 * keyed on the kind being "cv"; nested results on the run's `nested` flag.
 * RunResults hides predictions and reports for the "full" kind by passing
 * `supportsPredictions = kind !== "full"`, mirrored here.
 */

import React from "react";
import { screen } from "@testing-library/react";

let mockKind = null;
let mockSession = null;

jest.mock("../ModelsContext", () => ({
  useModels: () => ({ selectedSession: mockSession }),
}));

jest.mock("../../../hooks/useStrategyKind", () => ({
  useStrategyKind: () => mockKind,
}));

import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import ResultsTabsHeader from "./ResultsTabsHeader";

const renderHeader = ({
  kind,
  splits = { test_size: 0.2 },
  run = { id: 1, nested: false },
  isFinished = true,
  optimizables = 2,
} = {}) => {
  mockKind = kind;
  mockSession = {
    evaluation_strategy: "SomeStrategy",
    splits: JSON.stringify(splits),
  };
  renderWithProviders(
    <ResultsTabsHeader
      activeTab={0}
      onTabChange={jest.fn()}
      isFinished={isFinished}
      optimizables={optimizables}
      explainerCount={1}
      predictionCount={2}
      reportCount={3}
      supportsPredictions={kind !== "full"}
      run={run}
    />,
  );
};

// [label, enabled] for every tab in render order; chip counts stripped.
const tabs = () =>
  screen
    .getAllByRole("tab")
    .map((tab) => [tab.textContent.replace(/\d+$/, ""), !tab.disabled]);

describe("ResultsTabsHeader for a finished run", () => {
  test("holdout: no cross validation row", () => {
    renderHeader({ kind: "holdout" });
    expect(tabs()).toEqual([
      ["Live Metrics", true],
      ["Hyperparameters", true],
      ["Explainability", true],
      ["Predictions", true],
      ["Reports", true],
    ]);
  });

  test("cv: fold graphs shown, nested results shown but disabled", () => {
    renderHeader({ kind: "cv" });
    expect(tabs()).toEqual([
      ["Live Metrics", true],
      ["Hyperparameters", true],
      ["Fold Graphs", true],
      ["Nested results", false],
      ["Explainability", true],
      ["Predictions", true],
      ["Reports", true],
    ]);
  });

  test("cv nested (run.nested): nested results enabled", () => {
    renderHeader({ kind: "cv", run: { id: 1, nested: true } });
    expect(tabs()).toEqual([
      ["Live Metrics", true],
      ["Hyperparameters", true],
      ["Fold Graphs", true],
      ["Nested results", true],
      ["Explainability", true],
      ["Predictions", true],
      ["Reports", true],
    ]);
  });

  test("a nested run under a non-cv kind gets no nested tab", () => {
    renderHeader({ kind: "holdout", run: { id: 1, nested: true } });
    expect(tabs().map(([label]) => label)).not.toContain("Nested results");
  });

  test("full: no cross validation row, no predictions nor reports", () => {
    renderHeader({ kind: "full", splits: {} });
    expect(tabs()).toEqual([
      ["Live Metrics", true],
      ["Hyperparameters", true],
      ["Explainability", true],
    ]);
  });

  test("unknown kind (still loading) reads as holdout", () => {
    renderHeader({ kind: null });
    expect(tabs().map(([label]) => label)).toEqual([
      "Live Metrics",
      "Hyperparameters",
      "Explainability",
      "Predictions",
      "Reports",
    ]);
  });

  test("cv without reserved rows: explainability disabled", () => {
    renderHeader({ kind: "cv", splits: { test_size: 0 } });
    expect(tabs()).toContainEqual(["Explainability", false]);
  });

  test("cv with the legacy holdout key still counts as reserved rows", () => {
    renderHeader({ kind: "cv", splits: { holdout: 0.2 } });
    expect(tabs()).toContainEqual(["Explainability", true]);
  });

  test("holdout explains regardless of the splits", () => {
    renderHeader({ kind: "holdout", splits: { test_size: 0 } });
    expect(tabs()).toContainEqual(["Explainability", true]);
  });

  test("no optimizable parameters: hyperparameters disabled", () => {
    renderHeader({ kind: "holdout", optimizables: 0 });
    expect(tabs()).toContainEqual(["Hyperparameters", false]);
  });
});

describe("ResultsTabsHeader for an unfinished run", () => {
  test("only live metrics is enabled", () => {
    renderHeader({
      kind: "cv",
      isFinished: false,
      run: { id: 1, nested: true },
    });
    expect(tabs()).toEqual([
      ["Live Metrics", true],
      ["Hyperparameters", false],
      ["Fold Graphs", false],
      ["Nested results", false],
      ["Explainability", false],
      ["Predictions", false],
      ["Reports", false],
    ]);
  });
});
