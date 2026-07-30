import React from "react";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";

// plotly.js pulls in mapbox-gl, which needs URL.createObjectURL and so cannot
// load under jsdom.
jest.mock("react-plotly.js", () => () => null);

jest.mock("../../../api/diagnostic", () => ({
  getDiagnostics: jest.fn(),
  getDiagnosticArtifacts: jest.fn(),
  deleteDiagnostic: jest.fn(),
}));
jest.mock("../../../api/component", () => ({
  getComponents: jest.fn(),
}));

import DiagnosticResultsTab from "./DiagnosticResultsTab";
import {
  getDiagnostics,
  getDiagnosticArtifacts,
} from "../../../api/diagnostic";
import { getComponents } from "../../../api/component";

const run = { id: 3 };
const session = { task_name: "TabularClassificationTask" };

const diagnosticRow = (overrides = {}) => ({
  id: 11,
  run_id: 3,
  diagnostic_name: "ConfusionMatrix",
  split: "test",
  status: 3,
  ...overrides,
});

describe("DiagnosticResultsTab", () => {
  beforeEach(() => {
    // CRA's jest config sets resetMocks, which strips implementations given in
    // the module factory, so they are (re)applied per test here.
    getDiagnosticArtifacts.mockResolvedValue([]);
    getComponents.mockResolvedValue([]);
  });

  it("invites the user to the sidebar when there are none", async () => {
    getDiagnostics.mockResolvedValue([]);

    renderWithProviders(<DiagnosticResultsTab run={run} session={session} />);

    expect(await screen.findByText(/no diagnostics yet/i)).toBeInTheDocument();
  });

  it("renders a card per diagnostic with its split", async () => {
    getDiagnostics.mockResolvedValue([
      diagnosticRow(),
      diagnosticRow({ id: 12, split: "train" }),
    ]);

    renderWithProviders(<DiagnosticResultsTab run={run} session={session} />);

    expect(await screen.findByText("Test")).toBeInTheDocument();
    expect(await screen.findByText("Train")).toBeInTheDocument();
  });

  it("renders the artifacts of a finished diagnostic", async () => {
    getDiagnostics.mockResolvedValue([diagnosticRow()]);
    getDiagnosticArtifacts.mockResolvedValue([
      { type: "text", payload: "matrix output", title: null, index: 0 },
    ]);

    renderWithProviders(<DiagnosticResultsTab run={run} session={session} />);

    const rendered = await screen.findAllByText("matrix output");
    expect(rendered.length).toBeGreaterThan(0);
  });

  it("reports a failed diagnostic without fetching artifacts", async () => {
    getDiagnostics.mockResolvedValue([diagnosticRow({ status: 4 })]);

    renderWithProviders(<DiagnosticResultsTab run={run} session={session} />);

    expect(await screen.findByText(/failed to compute/i)).toBeInTheDocument();
    await waitFor(() => expect(getDiagnosticArtifacts).not.toHaveBeenCalled());
  });
});
