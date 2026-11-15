/**
 * The reduction model's regressor is a nested form that the run dialog draws
 * from the backend's schema, with no code of its own: the field declares its
 * parent, the form lists the parent's children and resolves the placeholder
 * through the nested model's own schema (RECONCILING_FORECASTING §8.6,
 * slice 7).
 *
 * The schemas come from reductionForecasterForm.json, which pytest keeps equal
 * to what the API serves (tests/back/api/test_reduction_form_fixture.py), and
 * the parameters the form submits are checked against the file's payload,
 * which the same pytest module posts to POST /run/ and trains.
 */

import React from "react";
import { screen, waitFor } from "@testing-library/react";

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));

jest.mock("../../api/component", () => ({ getComponents: jest.fn() }));

import { renderWithProviders } from "../../test-utils/renderWithProviders";
import { getComponents } from "../../api/component";
import FormSchema from "../shared/FormSchema";
import FormSchemaLayout from "../shared/FormSchemaLayout";
import form from "./__fixtures__/reductionForecasterForm.json";

const MODEL = "RecursiveRegressionForecaster";

beforeEach(() => {
  getComponents.mockReset();
  getComponents.mockImplementation(async ({ model, componentParent } = {}) => {
    if (model === MODEL) return form.model;
    if (model === "LinearRegression") return form.regressor;
    if (componentParent) return form.parents;
    throw new Error(`unexpected request ${JSON.stringify({ model })}`);
  });
});

function renderForm() {
  const formRef = { current: null };
  renderWithProviders(
    <FormSchemaLayout>
      <FormSchema
        autoSave
        hideButtons
        model={MODEL}
        onFormSubmit={jest.fn()}
        setError={jest.fn()}
        formSubmitRef={formRef}
      />
    </FormSchemaLayout>,
  );
  return formRef;
}

it("lists the regressors of the parent the field declares", async () => {
  renderForm();

  await waitFor(() =>
    expect(getComponents).toHaveBeenCalledWith({
      componentParent: form.model.schema.properties.regressor.parent,
    }),
  );
  expect(form.model.schema.properties.regressor.parent).toBe(
    "SklearnLikeRegressor",
  );
});

it("selects the regressor of the placeholder", async () => {
  renderForm();

  expect(await screen.findByText("Regressor")).toBeInTheDocument();
  await waitFor(() =>
    expect(screen.getByDisplayValue("LinearRegression")).toBeInTheDocument(),
  );
});

it("submits the parameters the backend trains", async () => {
  const formRef = renderForm();

  await waitFor(() => expect(formRef.current?.values?.regressor).toBeTruthy());
  expect(formRef.current.values).toEqual(form.payload);
});
