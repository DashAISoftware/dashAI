import React from "react";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import DatasetSelector from "./DatasetSelector";
import { getPredictionSplits } from "../../api/predict";
import { getDatasetTypesByFilePath } from "../../api/datasets";

const mockColumns = {
  inputs: ["age", "income"],
  rawInputs: ["age", "income"],
  target: "label",
};

jest.mock("../../api/predict", () => ({ getPredictionSplits: jest.fn() }));
jest.mock("../../api/datasets", () => ({
  getDatasetFile: jest.fn(),
  getDatasetFileFiltered: jest.fn(),
  getDatasetTypesByFilePath: jest.fn(),
}));
// The session's columns by role, labelled as the task labels its roles.
const mockRoleColumns = [
  { name: "features", label: "Features", columns: ["age", "income"] },
  { name: "target", label: "Target", columns: ["label"] },
];

jest.mock("../../hooks/useTaskMetadata", () => ({
  useSessionColumns: () => mockColumns,
  useSessionRoleColumns: () => mockRoleColumns,
}));
jest.mock("../notebooks/dataset/DatasetTable", () => () => (
  <div data-testid="dataset-table" />
));

const training = { id: 4, name: "iris", file_path: "/d/iris" };
const other = { id: 5, name: "other", file_path: "/d/other" };
const experiment = { id: 1, task_name: "TabularClassificationTask" };

const threeSplits = [
  { name: "all", rows: 150 },
  { name: "train", rows: 90 },
  { name: "val", rows: 30 },
  { name: "test", rows: 30 },
];

function renderSelector(props = {}) {
  const onSplitChange = jest.fn();
  renderWithProviders(
    <DatasetSelector
      experiment={experiment}
      datasets={[training, other]}
      selectedDataset={training}
      setSelectedDataset={() => {}}
      runId={3}
      onSplitChange={onSplitChange}
      {...props}
    />,
  );
  return { onSplitChange };
}

describe("DatasetSelector (x/y run)", () => {
  beforeEach(() => {
    getDatasetTypesByFilePath.mockResolvedValue({});
    getPredictionSplits.mockResolvedValue({
      splits: threeSplits,
      trainingDatasetId: 4,
    });
  });

  describe("prediction info", () => {
    it("lists the columns of each role, labelled as the task labels it", async () => {
      renderSelector();

      const info = screen.getByRole("alert");
      expect(within(info).getByText("Prediction Info")).toBeInTheDocument();
      expect(within(info).getByText("Features:")).toBeInTheDocument();
      expect(within(info).getByText("age")).toBeInTheDocument();
      expect(within(info).getByText("income")).toBeInTheDocument();
      expect(within(info).getByText("Target:")).toBeInTheDocument();
      expect(within(info).getByText("label")).toBeInTheDocument();
      await screen.findByRole("radiogroup");
    });

    it("shows the dataset's table", async () => {
      renderSelector();

      expect(screen.getByTestId("dataset-table")).toBeInTheDocument();
      await waitFor(() =>
        expect(getDatasetTypesByFilePath).toHaveBeenCalledWith("/d/iris"),
      );
    });

    it("shows no info until a dataset is chosen", async () => {
      renderSelector({ selectedDataset: null });

      await waitFor(() => expect(getPredictionSplits).toHaveBeenCalledWith(3));
      expect(screen.queryByText("Features:")).not.toBeInTheDocument();
      expect(screen.queryByText("Target:")).not.toBeInTheDocument();
      expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
    });
  });

  describe("partition selector", () => {
    it("offers the run's partitions on its training dataset", async () => {
      const { onSplitChange } = renderSelector();

      const group = await screen.findByRole("radiogroup");
      expect(screen.getByText("Dataset Split")).toBeInTheDocument();
      expect(
        screen.getByText(
          "This is the dataset the model was trained on, so a single partition of it can be predicted instead of every row.",
        ),
      ).toBeInTheDocument();
      const radios = within(group).getAllByRole("radio");
      expect(radios.map((r) => r.value)).toEqual([
        "all",
        "train",
        "val",
        "test",
      ]);
      expect(within(group).getByLabelText("All")).toBeChecked();
      expect(within(group).getByLabelText("Train")).toBeInTheDocument();
      expect(within(group).getByLabelText("Validation")).toBeInTheDocument();
      expect(within(group).getByLabelText("Test")).toBeInTheDocument();
      expect(
        screen.getByText("150 rows will be predicted"),
      ).toBeInTheDocument();
      expect(onSplitChange).toHaveBeenLastCalledWith("all");
    });

    it("reports the partition the user picks", async () => {
      const { onSplitChange } = renderSelector();

      const group = await screen.findByRole("radiogroup");
      userEvent.click(within(group).getByLabelText("Test"));

      expect(within(group).getByLabelText("Test")).toBeChecked();
      expect(onSplitChange).toHaveBeenLastCalledWith("test");
      expect(screen.getByText("30 rows will be predicted")).toBeInTheDocument();
    });

    it("is hidden on a dataset other than the training one", async () => {
      const { onSplitChange } = renderSelector({ selectedDataset: other });

      await waitFor(() => expect(getPredictionSplits).toHaveBeenCalledWith(3));
      await screen.findByText("Features:");
      expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
      expect(screen.queryByText("Dataset Split")).not.toBeInTheDocument();
      expect(onSplitChange).toHaveBeenLastCalledWith("all");
      expect(onSplitChange).not.toHaveBeenCalledWith("train");
    });

    it("is hidden when the run has no partitions", async () => {
      getPredictionSplits.mockResolvedValue({
        splits: [],
        trainingDatasetId: 4,
      });
      const { onSplitChange } = renderSelector();

      await waitFor(() => expect(getPredictionSplits).toHaveBeenCalledWith(3));
      await screen.findByText("Features:");
      expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
      expect(onSplitChange).toHaveBeenLastCalledWith("all");
    });

    it("defaults to the first partition when the whole dataset is not offered", async () => {
      getPredictionSplits.mockResolvedValue({
        splits: [{ name: "test", rows: 12 }],
        trainingDatasetId: 4,
      });
      const { onSplitChange } = renderSelector();

      const group = await screen.findByRole("radiogroup");
      expect(within(group).getByLabelText("Test")).toBeChecked();
      expect(
        screen.getByText(
          "This model forecasts forward only, so it can be asked about the rows after the data it was fitted on and no others.",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("12 rows will be predicted")).toBeInTheDocument();
      await waitFor(() =>
        expect(onSplitChange).toHaveBeenLastCalledWith("test"),
      );
    });

    it("does not ask for partitions without a run", async () => {
      renderSelector({ runId: null });

      await screen.findByText("Features:");
      expect(getPredictionSplits).not.toHaveBeenCalled();
      expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
    });
  });
});
