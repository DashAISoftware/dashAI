/**
 * The generated form of a splitter marks a value outside its schema's bounds,
 * as the forms of the models do, and reports the form as invalid. The splits
 * step reads that report to ask for no preview with such a value, so the
 * backend's untranslated validation error never reaches the user.
 */

import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));

jest.mock("../../api/component", () => ({ getComponents: jest.fn() }));

import { renderWithProviders } from "../../test-utils/renderWithProviders";
import { getComponents } from "../../api/component";
import FormSchema from "./FormSchema";
import FormSchemaLayout from "./FormSchemaLayout";

// What GET /api/v1/component?model=RollingOriginSplitter serves, in English:
//   uv run python -c "import json; \
//     from DashAI.back.splitters.rolling_origin import RollingOriginSplitter; \
//     from DashAI.back.core.utils import localize; \
//     print(json.dumps(localize(RollingOriginSplitter.get_schema(), 'en')))"
const rollingOriginWireSchema = {
  additionalProperties: false,
  description: "Schema that configures the rolling origin splitter.",
  properties: {
    horizon: {
      description:
        "How many steps ahead the model is scored, from every origin and on the test. A step is one period of the series: a month on a monthly series.",
      minimum: 1,
      placeholder: 6,
      title: "Horizon",
      type: "integer",
    },
    n_origins: {
      description:
        "How many validation windows the model is scored on, each one horizon after the last and each with more history.",
      minimum: 2,
      placeholder: 3,
      title: "Number of origins",
      type: "integer",
    },
  },
  required: ["horizon", "n_origins"],
  title: "RollingOriginSplitterSchema",
  type: "object",
};

it("marks a value under the schema's minimum and reports the form as invalid", async () => {
  getComponents.mockResolvedValue({ schema: rollingOriginWireSchema });
  const setError = jest.fn();
  renderWithProviders(
    <FormSchemaLayout>
      <FormSchema
        autoSave
        hideButtons
        model="RollingOriginSplitter"
        onFormSubmit={jest.fn()}
        setError={setError}
      />
    </FormSchemaLayout>,
  );

  const field = await screen.findByDisplayValue("3");
  expect(field).not.toHaveAttribute("aria-invalid", "true");

  fireEvent.change(field, { target: { value: "0" } });

  await waitFor(() => expect(field).toHaveAttribute("aria-invalid", "true"));
  await waitFor(() => expect(setError).toHaveBeenLastCalledWith(true));

  fireEvent.change(field, { target: { value: "2" } });

  await waitFor(() => expect(field).toHaveAttribute("aria-invalid", "false"));
  await waitFor(() => expect(setError).toHaveBeenLastCalledWith(false));
});
