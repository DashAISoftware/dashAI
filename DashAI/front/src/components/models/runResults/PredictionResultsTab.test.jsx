import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import PredictionResultsTab from "./PredictionResultsTab";
const mockProps = { card: [], manual: [], panel: [] };

jest.mock("../PredictionCard", () => (props) => {
  mockProps.card.push(props);
  return (
    <div data-testid="prediction-card">
      {`card ${props.prediction.id} #${props.displayNumber}`}
    </div>
  );
});
jest.mock("../ManualPredictionsTable", () => (props) => {
  mockProps.manual.push(props);
  return (
    <div data-testid="manual-table">
      {props.predictions.map((p) => `manual ${p.id}`).join(",")}
    </div>
  );
});
jest.mock("../DatasetPredictionPanel", () => (props) => {
  mockProps.panel.push(props);
  return <div data-testid="dataset-panel" />;
});

const run = { id: 3, model_session_id: 1 };
const session = { id: 1, task_name: "TabularClassificationTask" };

const predictions = [
  { id: 10, dataset_id: 4, status: 3 },
  { id: 11, dataset_id: null, status: 3 },
  { id: 12, dataset_id: 5, status: 3 },
  { id: 13, status: 3 },
];

function renderTab(props = {}) {
  const defaults = {
    run,
    session,
    predictions,
    predictionDisplayNumbers: new Map([
      [10, 1],
      [11, 2],
      [12, 3],
      [13, 4],
    ]),
    outputColumn: "label",
    trainingDatasetSample: { a: 1 },
    showDatasetPanel: false,
    setShowDatasetPanel: jest.fn(),
    onSaved: jest.fn(),
    onDelete: jest.fn(),
    onUpdate: jest.fn(),
  };
  const merged = { ...defaults, ...props };
  return {
    ...renderWithProviders(<PredictionResultsTab {...merged} />),
    props: merged,
  };
}

describe("PredictionResultsTab (x/y run)", () => {
  beforeEach(() => {
    mockProps.card = [];
    mockProps.manual = [];
    mockProps.panel = [];
  });

  it("shows the Dataset / Manual toggle with Dataset selected", () => {
    renderTab();

    const datasetToggle = screen.getByRole("button", {
      name: "Dataset Predictions",
    });
    const manualToggle = screen.getByRole("button", {
      name: "Manual Predictions",
    });
    expect(datasetToggle).toHaveAttribute("aria-pressed", "true");
    expect(manualToggle).toHaveAttribute("aria-pressed", "false");
  });

  it("lists only the predictions with a dataset as cards in Dataset mode", () => {
    renderTab();

    const cards = screen.getAllByTestId("prediction-card");
    expect(cards.map((c) => c.textContent)).toEqual([
      "card 10 #1",
      "card 12 #3",
    ]);
    expect(screen.queryByTestId("manual-table")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Add New Prediction" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Add Row" }),
    ).not.toBeInTheDocument();
  });

  it("passes the target column and the training sample to each card", () => {
    renderTab();

    const props = mockProps.card[0];
    expect(props.targetColumn).toBe("label");
    expect(props.datasetSample).toEqual({ a: 1 });
  });

  it("says there are no dataset predictions when none has a dataset", () => {
    renderTab({ predictions: [{ id: 11, dataset_id: null }] });

    expect(screen.getByText("No dataset predictions yet")).toBeInTheDocument();
    expect(screen.queryByTestId("prediction-card")).not.toBeInTheDocument();
  });

  it("shows the manual table with only the predictions without a dataset", () => {
    renderTab();

    userEvent.click(screen.getByRole("button", { name: "Manual Predictions" }));

    expect(screen.getByTestId("manual-table")).toHaveTextContent(
      "manual 11,manual 13",
    );
    expect(screen.queryByTestId("prediction-card")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Row" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Run Prediction" }),
    ).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Add New Prediction" }),
    ).not.toBeInTheDocument();

    const tableProps = mockProps.manual.at(-1);
    expect(tableProps.run).toBe(run);
    expect(tableProps.session).toBe(session);
    expect(tableProps.targetColumn).toBe("label");
    expect(tableProps.datasetSample).toEqual({ a: 1 });
  });

  it("goes back to the cards when Dataset is chosen again", () => {
    renderTab();

    userEvent.click(screen.getByRole("button", { name: "Manual Predictions" }));
    userEvent.click(
      screen.getByRole("button", { name: "Dataset Predictions" }),
    );

    expect(screen.getAllByTestId("prediction-card")).toHaveLength(2);
    expect(screen.queryByTestId("manual-table")).not.toBeInTheDocument();
  });

  it("keeps the current mode when the selected toggle is clicked again", () => {
    renderTab();

    userEvent.click(
      screen.getByRole("button", { name: "Dataset Predictions" }),
    );

    expect(
      screen.getByRole("button", { name: "Dataset Predictions" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByTestId("prediction-card")).toHaveLength(2);
  });

  it("opens the dataset dialog from Add New Prediction", () => {
    const { props } = renderTab();

    userEvent.click(screen.getByRole("button", { name: "Add New Prediction" }));

    expect(props.setShowDatasetPanel).toHaveBeenCalledWith(true);
  });

  it("renders the DatasetPredictionPanel inside the dialog when it is open", () => {
    renderTab({ showDatasetPanel: true });

    expect(screen.getByText("New Dataset Prediction")).toBeInTheDocument();
    expect(screen.getByTestId("dataset-panel")).toBeInTheDocument();
    const panelProps = mockProps.panel.at(-1);
    expect(panelProps.run).toBe(run);
    expect(panelProps.session).toBe(session);
  });

  it("does not render the DatasetPredictionPanel while the dialog is closed", () => {
    renderTab({ showDatasetPanel: false });

    expect(screen.queryByTestId("dataset-panel")).not.toBeInTheDocument();
  });

  it("closes the dialog and reports the prediction the panel saved", () => {
    const { props } = renderTab({ showDatasetPanel: true });

    const panelProps = mockProps.panel.at(-1);
    panelProps.onSaved({ id: 99, dataset_id: 4 });

    expect(props.onSaved).toHaveBeenCalledWith({ id: 99, dataset_id: 4 });
    expect(props.setShowDatasetPanel).toHaveBeenCalledWith(false);
  });
});
