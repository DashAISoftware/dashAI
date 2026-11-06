import { exogenousNotice } from "./exogenous";

/*
 * What the run dialog says about a model and the session's exogenous
 * variables: the backend's mark, crossed with the value the form gives the
 * parameter the mark names as the switch (RECONCILING_FORECASTING §7.2,
 * decision 7). No domain logic: two declarations and a form value.
 */

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

describe("exogenousNotice", () => {
  it("says nothing for a model that will read them", () => {
    expect(exogenousNotice(declared, "ARIMA", {})).toBeNull();
    expect(
      exogenousNotice(declared, "ARIMA", { use_exogenous: true }),
    ).toBeNull();
  });

  it("gives the backend's reason for a model that will not", () => {
    expect(exogenousNotice(declared, "NaiveForecaster", {})).toEqual({
      key: "modelTakesNoExogenous",
      values: { model: "NaiveForecaster" },
    });
  });

  it("says the switch is off while the form has it off", () => {
    expect(
      exogenousNotice(declared, "ARIMA", { use_exogenous: false }),
    ).toEqual({ key: "exogenousSwitchedOff", values: { model: "ARIMA" } });
  });

  it("says nothing without a declaration or for a model it does not list", () => {
    expect(exogenousNotice(null, "ARIMA", {})).toBeNull();
    expect(exogenousNotice({ models: [] }, "ARIMA", {})).toBeNull();
  });
});
