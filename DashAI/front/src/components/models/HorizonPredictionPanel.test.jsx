import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import i18n from "../../utils/i18n";
import { createPrediction, getPredictionSplits } from "../../api/predict";
import { enqueuePredictionJob } from "../../api/job";
import HorizonPredictionPanel from "./HorizonPredictionPanel";

/*
 * The horizon form of a task that predicts by horizon. The warning about
 * steps no backtest measured comes with the answer of POST /predict/, and
 * belongs to the horizon it was asked for.
 */

jest.mock("../../api/predict", () => ({
  createPrediction: jest.fn(),
  getPredictionSplits: jest.fn(),
}));
jest.mock("../../api/job", () => ({ enqueuePredictionJob: jest.fn() }));
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
  enqueuePredictionJob.mockResolvedValue({});
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
});
