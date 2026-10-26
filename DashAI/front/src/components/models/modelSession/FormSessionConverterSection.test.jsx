/**
 * The session wizard's converter form starts from the session's own defaults.
 *
 * The encoders' schemas are strict, as the notebook uses them: there a
 * converter may be fitted on some rows and applied to all of them, and what
 * it writes is saved. A session fits on the training rows only, so it treats
 * a category it did not see, and the backend declares those defaults in each
 * converter's `metadata.session_params`. The form is the real one, fed the
 * schema the backend serves, so what is saved is what the wizard would send.
 */

import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// See FormSchemaRenderFields.test.jsx: react-markdown is ESM only.
jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));

jest.mock("../../../api/component", () => ({
  getComponents: jest.fn(),
}));

import { getComponents } from "../../../api/component";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import FormSessionConverterSection from "./FormSessionConverterSection";

const DTYPE = {
  enum: ["int32", "int64"],
  enumNames: ["32-bit integer", "64-bit integer"],
  placeholder: "int64",
  title: "Dtype",
  type: "string",
};

// The schemas as the backend serves them, trimmed to the fields that matter.
const CONVERTERS = {
  OneHotEncoder: {
    schema: {
      type: "object",
      title: "OneHotEncoderSchema",
      required: ["dtype", "handle_unknown"],
      properties: {
        dtype: DTYPE,
        handle_unknown: {
          enum: ["error", "ignore", "infrequent_if_exist"],
          enumNames: [
            "Raise an error",
            "Encode as all zeros",
            "Fold into the infrequent category",
          ],
          placeholder: "error",
          title: "Handle Unknown",
          type: "string",
        },
      },
    },
    session_params: { handle_unknown: "ignore" },
  },
  OrdinalEncoder: {
    schema: {
      type: "object",
      title: "OrdinalEncoderSchema",
      required: ["dtype", "handle_unknown", "unknown_value"],
      properties: {
        dtype: DTYPE,
        handle_unknown: {
          enum: ["error", "use_encoded_value"],
          enumNames: ["Raise an error", "Use the fallback value below"],
          placeholder: "error",
          title: "Handle Unknown",
          type: "string",
        },
        unknown_value: {
          anyOf: [
            { type: "integer" },
            {
              enum: ["np.nan"],
              enumNames: ["Not a number (NaN)"],
              type: "string",
            },
            { type: "null" },
          ],
          placeholder: null,
          title: "Unknown Value",
        },
      },
    },
    session_params: { handle_unknown: "use_encoded_value", unknown_value: -1 },
  },
};

async function saveWithTheDefaults(name) {
  const { schema, session_params } = CONVERTERS[name];
  getComponents.mockResolvedValue({ name, schema });
  const setNewExp = jest.fn();
  renderWithProviders(
    <FormSessionConverterSection
      step={1}
      setStep={jest.fn()}
      handleClose={jest.fn()}
      tool={{ name, schema, metadata: { session_params } }}
      newExp={{ preprocessing: [] }}
      setNewExp={setNewExp}
      finalState={[]}
      stepDisplayNames={[]}
    />,
  );

  // The form is drawn once the schema has arrived.
  await screen.findAllByText(/handle unknown/i);
  const save = await screen.findByRole("button", { name: /create converter/i });
  await waitFor(() => expect(save).toBeEnabled());
  await userEvent.click(save);

  await waitFor(() => expect(setNewExp).toHaveBeenCalled());
  return setNewExp.mock.calls[0][0].preprocessing[0].params;
}

describe("FormSessionConverterSection", () => {
  test("a one-hot step is saved treating an unseen category", async () => {
    expect(await saveWithTheDefaults("OneHotEncoder")).toEqual({
      dtype: "int64",
      handle_unknown: "ignore",
    });
  });

  test("an ordinal step is saved encoding an unseen category as -1", async () => {
    expect(await saveWithTheDefaults("OrdinalEncoder")).toEqual({
      dtype: "int64",
      handle_unknown: "use_encoded_value",
      unknown_value: -1,
    });
  });
});
