import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import i18n from "../../utils/i18n";
import {
  createPrediction,
  getFutureDates,
  getPredictionSplits,
  getPredictions,
} from "../../api/predict";
import { enqueuePredictionJob } from "../../api/job";
import { startJobPolling } from "../../utils/jobPoller";
import HorizonPredictionPanel from "./HorizonPredictionPanel";

/*
 * The horizon form of a task that predicts by horizon. The warning about
 * steps no backtest measured comes with the answer of POST /predict/, and
 * belongs to the horizon it was asked for.
 */

jest.mock("../../api/predict", () => ({
  createPrediction: jest.fn(),
  getFutureDates: jest.fn(),
  getPredictionSplits: jest.fn(),
  getPredictions: jest.fn(),
}));
// The dataset panel creates the prediction itself; the stand-in says it chose
// dataset 4 and, when clicked, hands back what POST /predict/ answered.
const mockDatasetPrediction = {
  id: 9,
  dataset_id: 4,
  unevaluated_steps: 1,
  evaluated_horizon: 3,
};
jest.mock("./DatasetPredictionPanel", () => {
  const { useEffect } = jest.requireActual("react");
  const Stub = ({ onCreated, onStateChange }) => {
    useEffect(() => {
      onStateChange?.({ canRun: true, isSubmitting: false, datasetId: 4 });
    }, [onStateChange]);
    return (
      <button type="button" onClick={() => onCreated?.(mockDatasetPrediction)}>
        future dataset panel
      </button>
    );
  };
  return Stub;
});
jest.mock("../../api/job", () => ({ enqueuePredictionJob: jest.fn() }));
jest.mock("../../utils/jobPoller", () => ({ startJobPolling: jest.fn() }));
jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn(), closeSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});

const warning = (count, evaluated) =>
  i18n.t("prediction:message.unevaluatedSteps", { count, evaluated });

const horizonField = () =>
  screen.getByLabelText(i18n.t("prediction:label.horizon"));

const run = async (steps) => {
  fireEvent.change(horizonField(), { target: { value: String(steps) } });
  fireEvent.click(
    screen.getByRole("button", {
      name: i18n.t("prediction:button.runPrediction"),
    }),
  );
  await waitFor(() => expect(enqueuePredictionJob).toHaveBeenCalled());
};

beforeEach(() => {
  createPrediction.mockReset();
  getPredictionSplits.mockReset();
  enqueuePredictionJob.mockReset();
  enqueuePredictionJob.mockResolvedValue({ id: 77 });
  getPredictions.mockReset();
  getPredictions.mockResolvedValue([]);
  startJobPolling.mockReset();
});

describe("HorizonPredictionPanel", () => {
  it("starts on the horizon the run measured", async () => {
    getPredictionSplits.mockResolvedValue({ splits: [], horizon: 6 });
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );

    await waitFor(() => expect(horizonField()).toHaveValue(6));
  });

  it("warns about the unmeasured steps of the horizon asked for, and only while the field holds it", async () => {
    getPredictionSplits.mockResolvedValue({ splits: [], horizon: 6 });
    createPrediction.mockResolvedValue({
      id: 9,
      unevaluated_steps: 4,
      evaluated_horizon: 6,
    });
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );
    await waitFor(() => expect(horizonField()).toHaveValue(6));

    await run(10);

    expect(createPrediction).toHaveBeenCalledWith(1, null, null, 10);
    expect(await screen.findByText(warning(4, 6))).toBeInTheDocument();

    fireEvent.change(horizonField(), { target: { value: "3" } });
    expect(screen.queryByText(warning(4, 6))).not.toBeInTheDocument();

    fireEvent.change(horizonField(), { target: { value: "10" } });
    expect(screen.getByText(warning(4, 6))).toBeInTheDocument();
  });

  it("names the horizon measured from the answer, when the prediction options could not be read", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    getPredictionSplits.mockRejectedValue(new Error("Network Error"));
    createPrediction.mockResolvedValue({
      id: 9,
      unevaluated_steps: 2,
      evaluated_horizon: 3,
    });
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );
    await waitFor(() => expect(getPredictionSplits).toHaveBeenCalled());

    await run(5);

    expect(await screen.findByText(warning(2, 3))).toBeInTheDocument();
    console.error.mockRestore();
  });

  it("warns about a single unmeasured step in the singular", async () => {
    getPredictionSplits.mockResolvedValue({ splits: [], horizon: 6 });
    createPrediction.mockResolvedValue({
      id: 9,
      unevaluated_steps: 1,
      evaluated_horizon: 6,
    });
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );
    await waitFor(() => expect(horizonField()).toHaveValue(6));

    await run(7);

    expect(
      await screen.findByText(
        "The last step goes beyond the 6 the backtest measured: its error was never evaluated.",
      ),
    ).toBeInTheDocument();
  });

  it("shows no warning for a horizon the backtest measured", async () => {
    getPredictionSplits.mockResolvedValue({ splits: [], horizon: 6 });
    createPrediction.mockResolvedValue({ id: 9 });
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );
    await waitFor(() => expect(horizonField()).toHaveValue(6));

    await run(6);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("watches the job it queued, so the queue shows it and the panel learns it finished", async () => {
    getPredictionSplits.mockResolvedValue({ splits: [], horizon: 6 });
    createPrediction.mockResolvedValue({ id: 9, status: 1 });
    const onSaved = jest.fn();
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={onSaved} />,
    );
    await waitFor(() => expect(horizonField()).toHaveValue(6));

    await run(6);

    await waitFor(() =>
      expect(startJobPolling).toHaveBeenCalledWith(
        77,
        expect.any(Function),
        expect.any(Function),
      ),
    );

    const finished = { id: 9, status: 3 };
    getPredictions.mockResolvedValue([{ id: 8, status: 3 }, finished]);
    const [, onSuccess] = startJobPolling.mock.calls[0];
    await onSuccess({ id: 77, status: "finished" });

    expect(getPredictions).toHaveBeenCalledWith(1);
    expect(onSaved).toHaveBeenLastCalledWith(finished);
  });

  it("refreshes the prediction when its job fails", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    getPredictionSplits.mockResolvedValue({ splits: [], horizon: 6 });
    createPrediction.mockResolvedValue({ id: 9, status: 1 });
    const onSaved = jest.fn();
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={onSaved} />,
    );
    await waitFor(() => expect(horizonField()).toHaveValue(6));

    await run(6);
    await waitFor(() => expect(startJobPolling).toHaveBeenCalled());

    const failed = { id: 9, status: 4 };
    getPredictions.mockResolvedValue([failed]);
    const [, , onError] = startJobPolling.mock.calls[0];
    await onError({ id: 77, status: "error", error: "boom" });

    expect(onSaved).toHaveBeenLastCalledWith(failed);
    console.error.mockRestore();
  });
});

describe("HorizonPredictionPanel, for a run that read exogenous variables", () => {
  const declared = {
    splits: [],
    horizon: 3,
    exogenous: { columns: [{ name: "promo", type: "Float" }] },
  };

  it("offers a dataset of the future rows, or typing them in", async () => {
    getPredictionSplits.mockResolvedValue(declared);
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );

    expect(await screen.findByText("future dataset panel")).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: i18n.t("prediction:label.futureTypedIn"),
      }),
    ).toBeInTheDocument();
  });

  it("types the future in on the next dates and sends it as the job's rows", async () => {
    getPredictionSplits.mockResolvedValue(declared);
    getFutureDates.mockResolvedValue({
      timeIndex: "date",
      dates: ["2024-01-01", "2024-02-01"],
    });
    createPrediction.mockResolvedValue({ id: 9 });
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );
    fireEvent.click(
      await screen.findByRole("button", {
        name: i18n.t("prediction:label.futureTypedIn"),
      }),
    );
    fireEvent.change(horizonField(), { target: { value: "2" } });
    fireEvent.click(
      screen.getByRole("button", {
        name: i18n.t("prediction:button.generateDates"),
      }),
    );
    await waitFor(() => expect(getFutureDates).toHaveBeenCalledWith(1, 2));

    fireEvent.change(await screen.findByLabelText("promo 2024-01-01"), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByLabelText("promo 2024-02-01"), {
      target: { value: "0" },
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: i18n.t("prediction:button.runPrediction"),
      }),
    );

    await waitFor(() =>
      expect(enqueuePredictionJob).toHaveBeenCalledWith(9, [
        { date: "2024-01-01", promo: 1 },
        { date: "2024-02-01", promo: 0 },
      ]),
    );
    // The horizon is the number of rows typed in.
    expect(createPrediction).toHaveBeenCalledWith(1, null, null, 2);
  });

  const typeIn = async (dates) => {
    getFutureDates.mockResolvedValueOnce({ timeIndex: "date", dates });
    fireEvent.change(horizonField(), {
      target: { value: String(dates.length) },
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: i18n.t("prediction:button.generateDates"),
      }),
    );
    // The table is the one for these dates once it has as many rows.
    await waitFor(() =>
      expect(screen.getAllByLabelText(/^promo /)).toHaveLength(dates.length),
    );
    for (const date of dates) {
      fireEvent.change(await screen.findByLabelText(`promo ${date}`), {
        target: { value: "1" },
      });
    }
  };

  it("warns about the rows typed in past the horizon measured, while there are that many", async () => {
    getPredictionSplits.mockResolvedValue(declared);
    createPrediction.mockResolvedValue({
      id: 9,
      unevaluated_steps: 2,
      evaluated_horizon: 3,
    });
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );
    fireEvent.click(
      await screen.findByRole("button", {
        name: i18n.t("prediction:label.futureTypedIn"),
      }),
    );
    const five = ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"];
    await typeIn([...five, "2024-05-01"]);

    fireEvent.click(
      screen.getByRole("button", {
        name: i18n.t("prediction:button.runPrediction"),
      }),
    );

    await waitFor(() =>
      expect(createPrediction).toHaveBeenCalledWith(1, null, null, 5),
    );
    expect(await screen.findByText(warning(2, 3))).toBeInTheDocument();

    // Editing the horizon field changes no row: the warning stays.
    fireEvent.change(horizonField(), { target: { value: "3" } });
    expect(screen.getByText(warning(2, 3))).toBeInTheDocument();

    await typeIn(["2024-01-01", "2024-02-01", "2024-03-01"]);
    expect(screen.queryByText(warning(2, 3))).not.toBeInTheDocument();
  });

  it("warns about the rows of a dataset past the horizon measured", async () => {
    getPredictionSplits.mockResolvedValue(declared);
    renderWithProviders(
      <HorizonPredictionPanel run={{ id: 1 }} onSaved={jest.fn()} />,
    );

    fireEvent.click(await screen.findByText("future dataset panel"));

    expect(await screen.findByText(warning(1, 3))).toBeInTheDocument();
  });
});
