import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import SelectDatasetStep from "./SelectDatasetStep";
import { getComponents } from "../../api/component";
import { getDatasets } from "../../api/datasets";
import { getExplainableSplits, getValidDatasets } from "../../api/explainer";
import { getRunById } from "../../api/run";
import { getModelSessionById } from "../../api/modelSession";

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn(), closeSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});
jest.mock("../../api/component", () => ({ getComponents: jest.fn() }));
jest.mock("../../api/datasets", () => ({
  getDatasets: jest.fn(),
  getDatasetInfo: jest.fn(),
  getDatasetFile: jest.fn(),
  getDatasetTypes: jest.fn(),
  getDatasetTypesByFilePath: jest.fn(),
  getDatasetSample: jest.fn(),
}));
jest.mock("../../api/explainer", () => ({
  getExplainableSplits: jest.fn(),
  getValidDatasets: jest.fn(),
}));
jest.mock("../../api/run", () => ({ getRunById: jest.fn() }));
jest.mock("../../api/modelSession", () => ({ getModelSessionById: jest.fn() }));
jest.mock("../shared/leanDatasetTable/LeanDatasetTable", () => () => null);
jest.mock("../notebooks/NoteBox", () => () => null);
jest.mock(
  "../notebooks/notebookCreation/DatasetAutocomplete",
  () => () => null,
);

describe("SelectDatasetStep", () => {
  it("says the session's task is not available instead of showing nothing", async () => {
    getDatasets.mockResolvedValue([]);
    getValidDatasets.mockResolvedValue([]);
    getExplainableSplits.mockResolvedValue([]);
    getRunById.mockResolvedValue({ id: 5, model_session_id: 1 });
    getModelSessionById.mockResolvedValue({
      id: 1,
      task_name: "UninstalledPluginTask",
      dataset_id: 2,
      column_roles: {},
    });
    getComponents.mockRejectedValue({
      response: {
        status: 404,
        data: { detail: "Component UninstalledPluginTask not found." },
      },
    });

    renderWithProviders(
      <SelectDatasetStep
        newExpl={{ run_id: 5 }}
        setNewExpl={jest.fn()}
        setNextEnabled={jest.fn()}
      />,
    );

    expect(
      await screen.findByText(
        "The task UninstalledPluginTask of this session is not available, " +
          "so the columns to explain cannot be read. It may belong to a " +
          "plugin that is no longer installed.",
      ),
    ).toBeInTheDocument();
  });
});
