/**
 * The "Edit Run" dialog saves only once the user has changed something.
 *
 * The parameters form seeds itself with the schema defaults under the run's
 * saved parameters, and hands the result back to the dialog. A run saved
 * without every field of its model's schema (a field added later, a run
 * created through the API) must not read as edited because of that seed.
 * The form is the real one, fed the schema the backend serves.
 */

import React from "react";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";

// See FormSchemaRenderFields.test.jsx: react-markdown is ESM only.
jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));

jest.mock("../../api/component", () => ({
  getComponents: jest.fn(),
}));

jest.mock("../../api/run", () => ({
  getRunOperationsCount: jest.fn(),
  updateRunParameters: jest.fn(),
}));

jest.mock("./ModelsContext", () => ({
  useModels: () => ({ selectedSession: null, datasetRowCount: 0 }),
}));

jest.mock("../../hooks/useStrategyKind", () => ({
  useStrategyKind: () => null,
}));

import { getComponents } from "../../api/component";
import { getRunOperationsCount } from "../../api/run";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import RunEditDialog from "./RunEditDialog";

const SCHEMA = {
  type: "object",
  title: "SlowModelSchema",
  required: ["depth", "leaves"],
  properties: {
    depth: { type: "integer", placeholder: 3, title: "Depth" },
    leaves: { type: "integer", placeholder: 8, title: "Leaves" },
  },
};

// Saved before ``leaves`` existed.
const RUN = {
  id: 1,
  name: "run",
  model_name: "SlowModel",
  parameters: { depth: 5 },
};

function renderDialog() {
  getComponents.mockResolvedValue({ name: "SlowModel", schema: SCHEMA });
  getRunOperationsCount.mockResolvedValue({});
  renderWithProviders(
    <RunEditDialog run={RUN} session={null} open onClose={jest.fn()} />,
  );
}

async function fieldsDrawn() {
  await screen.findAllByText(/leaves/i);
  return screen.getByRole("button", { name: /save/i });
}

describe("RunEditDialog", () => {
  test("a run saved without every schema field opens unchanged", async () => {
    renderDialog();
    const save = await fieldsDrawn();

    // The seed lands a few renders after the fields, and nothing on screen
    // shows it; let them all settle before looking at the button.
    await act(() => new Promise((resolve) => setTimeout(resolve, 100)));

    expect(save).toBeDisabled();
  });

  test("changing a parameter enables saving", async () => {
    renderDialog();
    const save = await fieldsDrawn();

    const [depth] = screen.getAllByRole("spinbutton");
    fireEvent.change(depth, { target: { value: "7" } });

    await waitFor(() => expect(save).toBeEnabled());
  });
});
