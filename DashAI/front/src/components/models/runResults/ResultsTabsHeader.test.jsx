/**
 * Which result tabs a finished run offers, by what the session's evaluation
 * strategy declares. The fold graphs and the forecasts tabs follow its
 * `result_views`; nested results stay a cross-validation feature, keyed on
 * the kind being "cv" and on the run's `nested` flag.
 * RunResults hides predictions and reports for the "full" kind by passing
 * `supportsPredictions = kind !== "full"`, mirrored here.
 */

import React from "react";
import { screen } from "@testing-library/react";

let mockKind = null;
let mockResultViews = [];
let mockSession = null;

jest.mock("../ModelsContext", () => ({
  useModels: () => ({ selectedSession: mockSession }),
}));

jest.mock("../../../hooks/useStrategyKind", () => ({
  useStrategyKind: () => mockKind,
  useStrategyMetadata: () =>
    mockKind === null
      ? null
      : { kind: mockKind, result_views: mockResultViews },
}));

// What each built-in strategy kind declares (BaseEvaluationStrategy).
const RESULT_VIEWS_BY_KIND = { cv: ["fold_metrics"] };

import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import ResultsTabsHeader from "./ResultsTabsHeader";

const renderHeader = ({
  kind,
  resultViews = RESULT_VIEWS_BY_KIND[kind] ?? [],
  splits = { test_size: 0.2 },
  run = { id: 1, nested: false },
  isFinished = true,
  optimizables = 2,
} = {}) => {
  mockKind = kind;
  mockResultViews = resultViews;
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

  test("a backtest with several origins: fold graphs and forecasts, no nested results", () => {
    renderHeader({
      kind: "backtest",
      resultViews: ["fold_metrics", "forecasts"],
      splits: { horizon: 3, n_origins: 3 },
    });
    expect(tabs()).toEqual([
      ["Live Metrics", true],
      ["Hyperparameters", true],
      ["Fold Graphs", true],
      ["Forecasts", true],
      ["Explainability", true],
      ["Predictions", true],
      ["Reports", true],
    ]);
  });

  test("a backtest with one origin: forecasts only", () => {
    renderHeader({
      kind: "backtest",
      resultViews: ["forecasts"],
      splits: { horizon: 3 },
    });
    const labels = tabs().map(([label]) => label);
    expect(labels).toContain("Forecasts");
    expect(labels).not.toContain("Fold Graphs");
    expect(labels).not.toContain("Nested results");
  });

  test("the fold graphs follow the declaration, not the kind", () => {
    renderHeader({ kind: "cv", resultViews: [] });
    expect(tabs().map(([label]) => label)).not.toContain("Fold Graphs");
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
