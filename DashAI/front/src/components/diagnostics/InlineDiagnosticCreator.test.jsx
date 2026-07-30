import React from "react";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";

jest.mock("react-plotly.js", () => () => null);
// react-markdown ships ESM that jest cannot transform. It reaches this test
// only through FormSchema's tooltips, which none of these cases exercise.
jest.mock("react-markdown", () => () => null);

jest.mock("../../api/diagnostic", () => ({
  createDiagnostic: jest.fn(),
}));
jest.mock("../../api/job", () => ({
  enqueueDiagnosticJob: jest.fn(),
}));
jest.mock("../../utils/jobPoller", () => ({
  startJobPolling: jest.fn(),
}));
jest.mock("../../hooks/useSchema", () => ({
  __esModule: true,
  default: jest.fn(),
}));
// FormSchema reaches axios through the component API, and axios ships ESM that
// jest cannot transform.
jest.mock("../../api/component", () => ({
  getComponents: jest.fn(() => Promise.resolve([])),
}));

import InlineDiagnosticCreator from "./InlineDiagnosticCreator";
import { createDiagnostic } from "../../api/diagnostic";
import { enqueueDiagnosticJob } from "../../api/job";
import useSchema from "../../hooks/useSchema";

const withoutParameters = { defaultValues: {}, loading: false };
const withParameters = { defaultValues: { bins: 30 }, loading: false };

describe("InlineDiagnosticCreator", () => {
  beforeEach(() => {
    // CRA's jest config sets resetMocks, so implementations are set per test.
    createDiagnostic.mockResolvedValue({ id: 42 });
    enqueueDiagnosticJob.mockResolvedValue({ id: "job-1" });
    useSchema.mockReturnValue(withoutParameters);
  });

  const render = (props = {}) =>
    renderWithProviders(
      <InlineDiagnosticCreator
        open
        runId={7}
        diagnosticName="ConfusionMatrix"
        displayName="Confusion Matrix"
        onCancel={() => {}}
        {...props}
      />,
    );

  it("skips the parameter step for a diagnostic that takes none", async () => {
    render();

    // One step is not a wizard: no stepper, and the action saves directly.
    expect(screen.queryByText(/configure parameters/i)).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /save/i })).toBeEnabled();
    expect(
      screen.queryByRole("button", { name: /next/i }),
    ).not.toBeInTheDocument();
  });

  it("saves straight from the split step when there are no parameters", async () => {
    const onCreated = jest.fn();
    render({ onCreated });

    fireEvent.click(await screen.findByRole("radio", { name: /train/i }));
    fireEvent.click(await screen.findByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(createDiagnostic).toHaveBeenCalledWith(
        7,
        "ConfusionMatrix",
        "train",
        expect.any(Object),
      ),
    );
    await waitFor(() => expect(enqueueDiagnosticJob).toHaveBeenCalledWith(42));
    await waitFor(() => expect(onCreated).toHaveBeenCalled());
  });

  it("shows the parameter step for a diagnostic that takes one", async () => {
    useSchema.mockReturnValue(withParameters);
    render({ diagnosticName: "ResidualHistogram" });

    expect(await screen.findByText(/select split/i)).toBeInTheDocument();
    expect(
      await screen.findByText(/configure parameters/i),
    ).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /next/i })).toBeEnabled();
  });

  it("can go back from the parameter step", async () => {
    useSchema.mockReturnValue(withParameters);
    render({ diagnosticName: "ResidualHistogram" });

    fireEvent.click(await screen.findByRole("button", { name: /next/i }));
    fireEvent.click(await screen.findByRole("button", { name: /back/i }));

    expect(await screen.findByRole("radio", { name: /test/i })).toBeChecked();
  });
});
