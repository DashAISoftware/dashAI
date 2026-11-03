import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import i18n from "../../utils/i18n";
import { getExogenousUse } from "../../api/modelSession";
import ExogenousUseNotice from "./ExogenousUseNotice";

jest.mock("../../api/modelSession", () => ({ getExogenousUse: jest.fn() }));

const declared = {
  has_exogenous: true,
  models: [
    { model: "ARIMA", uses: true, reason: null, switch: "use_exogenous" },
    {
      model: "NaiveForecaster",
      uses: false,
      reason: {
        key: "modelTakesNoExogenous",
        values: { model: "NaiveForecaster" },
      },
      switch: null,
    },
  ],
};

beforeEach(() => getExogenousUse.mockResolvedValue(declared));

describe("ExogenousUseNotice", () => {
  it("says why a model will not read the session's exogenous variables", async () => {
    renderWithProviders(
      <ExogenousUseNotice
        sessionId={3}
        model="NaiveForecaster"
        parameters={{}}
      />,
    );

    expect(
      await screen.findByText(
        i18n.t("models:exogenous.reason.modelTakesNoExogenous", {
          model: "NaiveForecaster",
        }),
      ),
    ).toBeInTheDocument();
    expect(getExogenousUse).toHaveBeenCalledWith(3);
  });

  it("says the switch is off while the form has it off", async () => {
    renderWithProviders(
      <ExogenousUseNotice
        sessionId={3}
        model="ARIMA"
        parameters={{ use_exogenous: false }}
      />,
    );

    expect(
      await screen.findByText(
        i18n.t("models:exogenous.reason.exogenousSwitchedOff", {
          model: "ARIMA",
        }),
      ),
    ).toBeInTheDocument();
  });
});
