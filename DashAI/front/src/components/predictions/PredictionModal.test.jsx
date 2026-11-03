import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import PredictionModal from "./PredictionModal";
import {
  createPrediction,
  filterDatasets,
  getPredictions,
} from "../../api/predict";
import {
  getDatasets,
  getDatasetTypes,
  getDatasetSample,
} from "../../api/datasets";
import { enqueuePredictionJob } from "../../api/job";
import { getModelSessionById } from "../../api/modelSession";

const mockProps = { selector: [], manual: [] };
const mockColumns = {
  inputs: ["age", "income"],
  rawInputs: ["age", "income"],
  target: "label",
};

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: () => {}, closeSnackbar: () => {} };
  return { useSnackbar: () => snackbar };
});
jest.mock("../../api/predict", () => ({
  createPrediction: jest.fn(),
  filterDatasets: jest.fn(),
  getPredictions: jest.fn(),
  deletePrediction: jest.fn(),
}));
jest.mock("../../api/datasets", () => ({
  getDatasets: jest.fn(),
  exportDatasetCsvByPath: jest.fn(),
  getDatasetTypes: jest.fn(),
  getDatasetSample: jest.fn(),
}));
jest.mock("../../api/job", () => ({ enqueuePredictionJob: jest.fn() }));
jest.mock("../../api/modelSession", () => ({ getModelSessionById: jest.fn() }));
jest.mock("../../hooks/useTaskMetadata", () => ({
  useSessionColumns: () => mockColumns,
}));
jest.mock("./DatasetSelector", () => (props) => {
  mockProps.selector.push(props);
  return (
    <div data-testid="dataset-selector">
      {props.datasets.map((ds) => (
        <button key={ds.id} onClick={() => props.setSelectedDataset(ds)}>
          {`pick ${ds.name}`}
        </button>
      ))}
      <button onClick={() => props.onSplitChange("test")}>split test</button>
      <button onClick={() => props.onSplitChange("all")}>split all</button>
    </div>
  );
});
jest.mock("./ManualInput", () => (props) => {
  mockProps.manual.push(props);
  return (
    <div data-testid="manual-input">
      <button
        onClick={() =>
          props.setManualInputData([
            { age: 30, income: 1000 },
            { age: 41, income: 2500 },
          ])
        }
      >
        fill rows
      </button>
    </div>
  );
});
jest.mock("./ResultsTable", () => (props) => (
  <div data-testid="results-table">
    {`results ${props.selectedPrediction?.id}`}
  </div>
));
jest.mock("./PredictionsTable", () => () => (
  <div data-testid="predictions-table" />
));

const run = {
  id: 3,
  experiment_id: 1,
  model_session_id: 1,
  model_name: { name: "RandomForest", display_name: "Random Forest" },
};

const datasets = [
  { id: 4, name: "iris", file_path: "/d/iris" },
  { id: 5, name: "other", file_path: "/d/other" },
  { id: 6, name: "incompatible", file_path: "/d/inc" },
];

async function renderModal() {
  renderWithProviders(<PredictionModal isOpen onClose={() => {}} run={run} />);
  await waitFor(() =>
    expect(mockProps.selector.at(-1)?.datasets).toHaveLength(2),
  );
}

describe("PredictionModal (x/y run)", () => {
  beforeEach(() => {
    mockProps.selector = [];
    mockProps.manual = [];
    getDatasets.mockResolvedValue(datasets);
    filterDatasets.mockResolvedValue([4, 5]);
    getPredictions.mockResolvedValue([]);
    getModelSessionById.mockResolvedValue({
      id: 1,
      dataset_id: 4,
      task_name: "TabularClassificationTask",
    });
    getDatasetTypes.mockResolvedValue({});
    getDatasetSample.mockResolvedValue({ age: [30], income: [1000] });
    createPrediction.mockResolvedValue({ id: 11, status: 0 });
    enqueuePredictionJob.mockResolvedValue({});
  });

  it("shows the mode selector with the dataset and manual modes", async () => {
    await renderModal();

    expect(screen.getByText("Model Prediction")).toBeInTheDocument();
    expect(screen.getByText("Random Forest")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Select how you want to provide input data for prediction",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Use Existing Dataset")).toBeInTheDocument();
    expect(screen.getByText("Manual Prediction")).toBeInTheDocument();
  });

  it("starts in dataset mode with the run's compatible datasets", async () => {
    await renderModal();

    expect(screen.getByTestId("dataset-selector")).toBeInTheDocument();
    expect(screen.queryByTestId("manual-input")).not.toBeInTheDocument();
    const props = mockProps.selector.at(-1);
    expect(props.runId).toBe(3);
    expect(props.datasets.map((ds) => ds.id)).toEqual([4, 5]);
    expect(filterDatasets).toHaveBeenCalledWith({ run_id: 3 });
  });

  it("cannot run until a dataset is chosen", async () => {
    await renderModal();

    expect(
      screen.getByRole("button", { name: "Run Prediction" }),
    ).toBeDisabled();

    userEvent.click(screen.getByRole("button", { name: "pick iris" }));

    expect(
      screen.getByRole("button", { name: "Run Prediction" }),
    ).toBeEnabled();
  });

  it("creates a dataset prediction without a split and enqueues it without rows", async () => {
    await renderModal();

    userEvent.click(screen.getByRole("button", { name: "pick iris" }));
    userEvent.click(screen.getByRole("button", { name: "Run Prediction" }));

    await waitFor(() =>
      expect(enqueuePredictionJob).toHaveBeenCalledWith(11, null),
    );
    expect(createPrediction).toHaveBeenCalledTimes(1);
    expect(createPrediction).toHaveBeenCalledWith(3, 4, null);
  });

  it("sends the split the selector reported", async () => {
    await renderModal();

    userEvent.click(screen.getByRole("button", { name: "pick other" }));
    userEvent.click(screen.getByRole("button", { name: "split test" }));
    userEvent.click(screen.getByRole("button", { name: "Run Prediction" }));

    await waitFor(() =>
      expect(enqueuePredictionJob).toHaveBeenCalledWith(11, null),
    );
    expect(createPrediction).toHaveBeenCalledWith(3, 5, "test");
  });

  it("sends a null split when the selector reports all", async () => {
    await renderModal();

    userEvent.click(screen.getByRole("button", { name: "pick iris" }));
    userEvent.click(screen.getByRole("button", { name: "split test" }));
    userEvent.click(screen.getByRole("button", { name: "split all" }));
    userEvent.click(screen.getByRole("button", { name: "Run Prediction" }));

    await waitFor(() => expect(createPrediction).toHaveBeenCalled());
    expect(createPrediction).toHaveBeenCalledWith(3, 4, null);
  });

  it("shows the new prediction's results after it is submitted", async () => {
    await renderModal();

    userEvent.click(screen.getByRole("button", { name: "pick iris" }));
    userEvent.click(screen.getByRole("button", { name: "Run Prediction" }));

    expect(await screen.findByTestId("results-table")).toHaveTextContent(
      "results 11",
    );
    expect(
      screen.getByRole("tab", { name: "Previous Predictions" }),
    ).toHaveAttribute("aria-selected", "true");
  });

  it("shows the manual input with the session's raw input columns", async () => {
    await renderModal();

    userEvent.click(screen.getByText("Manual Prediction"));

    expect(screen.getByTestId("manual-input")).toBeInTheDocument();
    expect(screen.queryByTestId("dataset-selector")).not.toBeInTheDocument();
    await waitFor(() => expect(mockProps.manual.at(-1).loading).toBe(false));
    expect(mockProps.manual.at(-1).inputColumns).toEqual(["age", "income"]);
    expect(
      screen.getByRole("button", { name: "Run Prediction" }),
    ).toBeDisabled();
  });

  it("creates a manual prediction with no dataset or split and enqueues its rows", async () => {
    await renderModal();

    userEvent.click(screen.getByText("Manual Prediction"));
    userEvent.click(screen.getByRole("button", { name: "fill rows" }));
    userEvent.click(screen.getByRole("button", { name: "Run Prediction" }));

    await waitFor(() =>
      expect(enqueuePredictionJob).toHaveBeenCalledWith(11, [
        { age: 30, income: 1000 },
        { age: 41, income: 2500 },
      ]),
    );
    expect(createPrediction).toHaveBeenCalledTimes(1);
    expect(createPrediction).toHaveBeenCalledWith(3, null, null);
  });

  it("ignores a dataset and split chosen before switching to manual", async () => {
    await renderModal();

    userEvent.click(screen.getByRole("button", { name: "pick iris" }));
    userEvent.click(screen.getByRole("button", { name: "split test" }));
    userEvent.click(screen.getByText("Manual Prediction"));
    userEvent.click(screen.getByRole("button", { name: "fill rows" }));
    userEvent.click(screen.getByRole("button", { name: "Run Prediction" }));

    await waitFor(() => expect(createPrediction).toHaveBeenCalled());
    expect(createPrediction).toHaveBeenCalledWith(3, null, null);
  });
});
