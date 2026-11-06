import React from "react";
import { act, waitFor } from "@testing-library/react";
import { useSnackbar } from "notistack";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import DatasetPredictionPanel from "./DatasetPredictionPanel";
import { createPrediction, filterDatasets } from "../../api/predict";
import { getDatasets } from "../../api/datasets";
import { getModelSessionById } from "../../api/modelSession";

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn(), closeSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});
jest.mock("../../api/predict", () => ({
  createPrediction: jest.fn(),
  filterDatasets: jest.fn(),
  getPredictions: jest.fn(),
}));
jest.mock("../../api/job", () => ({ enqueuePredictionJob: jest.fn() }));
jest.mock("../../api/datasets", () => ({ getDatasets: jest.fn() }));
jest.mock("../../api/modelSession", () => ({ getModelSessionById: jest.fn() }));
// The selector stand-in picks the first dataset offered, as a user would.
jest.mock("../predictions/DatasetSelector", () => {
  const { useEffect } = jest.requireActual("react");
  return function DatasetSelector({ datasets, setSelectedDataset }) {
    useEffect(() => {
      if (datasets[0]) setSelectedDataset(datasets[0]);
    }, [datasets, setSelectedDataset]);
    return null;
  };
});

describe("DatasetPredictionPanel", () => {
  beforeEach(() => {
    getDatasets.mockResolvedValue([]);
    getModelSessionById.mockResolvedValue({ id: 1 });
  });

  it("shows what the backend said when the datasets cannot be listed", async () => {
    filterDatasets.mockRejectedValue({
      message: "Request failed with status code 404",
      response: {
        status: 404,
        data: {
          detail: "Task UninstalledPluginTask not found in the registry.",
        },
      },
    });

    renderWithProviders(
      <DatasetPredictionPanel run={{ id: 3, model_session_id: 1 }} />,
    );

    await waitFor(() =>
      expect(useSnackbar().enqueueSnackbar).toHaveBeenCalledWith(
        "Task UninstalledPluginTask not found in the registry.",
        { variant: "error" },
      ),
    );
  });

  it("falls back to its own message when the backend said nothing", async () => {
    filterDatasets.mockRejectedValue({ message: "Network Error" });

    renderWithProviders(
      <DatasetPredictionPanel run={{ id: 3, model_session_id: 1 }} />,
    );

    await waitFor(() =>
      expect(useSnackbar().enqueueSnackbar).toHaveBeenCalledWith(
        "Error loading prediction data",
        { variant: "error" },
      ),
    );
  });

  it("shows what the backend said when the prediction cannot be created", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    getDatasets.mockResolvedValue([{ id: 4, name: "future" }]);
    filterDatasets.mockResolvedValue([4]);
    createPrediction.mockRejectedValue({
      message: "Request failed with status code 422",
      response: {
        status: 422,
        data: { detail: "Run 3 read exogenous variables, so it forecasts..." },
      },
    });
    const runRef = { current: null };
    const onStateChange = jest.fn();

    renderWithProviders(
      <DatasetPredictionPanel
        run={{ id: 3, model_session_id: 1 }}
        onClose={jest.fn()}
        runRef={runRef}
        onStateChange={onStateChange}
      />,
    );
    await waitFor(() =>
      expect(onStateChange).toHaveBeenLastCalledWith(
        expect.objectContaining({ canRun: true, datasetId: 4 }),
      ),
    );
    await act(async () => runRef.current());

    expect(useSnackbar().enqueueSnackbar).toHaveBeenCalledWith(
      "Run 3 read exogenous variables, so it forecasts...",
      { variant: "error" },
    );
    console.error.mockRestore();
  });
});
