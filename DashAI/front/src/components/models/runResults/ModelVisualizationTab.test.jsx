import React from "react";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";

// plotly.js pulls in mapbox-gl, which needs URL.createObjectURL and so cannot
// load under jsdom. None of these cases render a plotly artifact.
jest.mock("react-plotly.js", () => () => null);

jest.mock("../../../api/run", () => ({
  getRunModelArtifacts: jest.fn(),
}));
jest.mock("../../../api/job", () => ({
  enqueueModelVisualizationJob: jest.fn(),
}));

import ModelVisualizationTab from "./ModelVisualizationTab";
import { getRunModelArtifacts } from "../../../api/run";
import { enqueueModelVisualizationJob } from "../../../api/job";

const run = { id: 7, model_name: "DecisionTreeClassifier", status: 3 };

describe("ModelVisualizationTab", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("offers generation when nothing has been generated yet", async () => {
    getRunModelArtifacts.mockResolvedValue({ status: null, artifacts: [] });

    renderWithProviders(<ModelVisualizationTab run={run} />);

    const button = await screen.findByRole("button", { name: /generate/i });
    expect(button).toBeEnabled();
  });

  it("enqueues the job when generate is clicked", async () => {
    getRunModelArtifacts.mockResolvedValue({ status: null, artifacts: [] });
    enqueueModelVisualizationJob.mockResolvedValue({ id: "job-1" });

    renderWithProviders(<ModelVisualizationTab run={run} />);

    fireEvent.click(await screen.findByRole("button", { name: /generate/i }));

    await waitFor(() =>
      expect(enqueueModelVisualizationJob).toHaveBeenCalledWith(7),
    );
  });

  it("renders stored artifacts", async () => {
    getRunModelArtifacts.mockResolvedValue({
      status: "FINISHED",
      artifacts: [
        { type: "text", payload: "tree dump", title: "Structure", index: 0 },
      ],
    });

    renderWithProviders(<ModelVisualizationTab run={run} />);

    // ArtifactViewer keeps its fullscreen lightbox mounted, so the payload
    // appears both in the card and in the (hidden) lightbox.
    const rendered = await screen.findAllByText("tree dump");
    expect(rendered.length).toBeGreaterThan(0);
  });

  it("reports a failed generation", async () => {
    getRunModelArtifacts.mockResolvedValue({ status: "ERROR", artifacts: [] });

    renderWithProviders(<ModelVisualizationTab run={run} />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("shows a generation already in flight as in progress", async () => {
    getRunModelArtifacts.mockResolvedValue({
      status: "STARTED",
      artifacts: [],
    });

    renderWithProviders(<ModelVisualizationTab run={run} />);

    const button = await screen.findByRole("button", { name: /generate/i });
    expect(button).toBeDisabled();
  });
});
