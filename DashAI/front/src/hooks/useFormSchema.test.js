/**
 * The shared form store is seeded once, with the schema's placeholders and
 * the caller's initial values over them. A schema that is still being
 * fetched must not let the initial values seed it alone: the form would then
 * submit only the fields they name.
 */

import React from "react";
import { renderHook, waitFor } from "@testing-library/react";

jest.mock("../api/component", () => ({
  getComponents: jest.fn(),
}));

import { getComponents } from "../api/component";
import { FormSchemaProvider, useFormSchemaStore } from "../contexts/schema";
import useFormSchema from "./useFormSchema";

const SCHEMA = {
  type: "object",
  title: "SlowSchema",
  required: ["dtype", "handle_unknown"],
  properties: {
    dtype: {
      enum: ["int32", "int64"],
      placeholder: "int64",
      title: "Dtype",
      type: "string",
    },
    handle_unknown: {
      enum: ["error", "ignore"],
      placeholder: "error",
      title: "Handle Unknown",
      type: "string",
    },
  },
};

const wrapper = ({ children }) => (
  <FormSchemaProvider>{children}</FormSchemaProvider>
);

test("initial values seed over the placeholders of a schema fetched later", async () => {
  let resolve;
  getComponents.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const initialValues = { handle_unknown: "ignore" };

  const { result } = renderHook(
    () => {
      useFormSchema({ model: "SlowConverter", initialValues });
      return useFormSchemaStore().formValues;
    },
    { wrapper },
  );
  resolve({ name: "SlowConverter", schema: SCHEMA });

  await waitFor(() =>
    expect(result.current).toEqual({
      dtype: "int64",
      handle_unknown: "ignore",
    }),
  );
});
