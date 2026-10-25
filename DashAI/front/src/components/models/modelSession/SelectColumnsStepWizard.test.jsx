import React from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import { getComponents } from "../../../api/component";
import {
  getPreprocessingStructure,
  validateColumns,
} from "../../../api/modelSession";
import SelectColumnsStep from "./SelectColumnsStep";
import RoleColumnSelectors from "./RoleColumnSelectors";

jest.mock("../../../api/component", () => ({ getComponents: jest.fn() }));
jest.mock("../../../api/modelSession", () => ({
  getPreprocessingStructure: jest.fn(),
  validateColumns: jest.fn(),
}));

const role = (name, label, overrides = {}) => ({
  name,
  label,
  types: ["Float"],
  min: 0,
  max: "n",
  required: false,
  transformable: true,
  ...overrides,
});
const SUPERVISED = {
  column_roles: [
    role("features", "Features"),
    role("target", "Target", {
      min: 1,
      max: 1,
      required: true,
      transformable: false,
      types: ["Categorical"],
    }),
  ],
  io_roles: { inputs: ["features"], outputs: ["target"] },
};
const raw = (name) => ({ kind: "raw", name });

const deferred = () => {
  let resolve;
  const promise = new Promise((r) => {
    resolve = r;
  });
  return { promise, resolve };
};

const renderSelect = (newExp = {}) => {
  const setNewExp = jest.fn();
  const setNextEnabled = jest.fn();
  renderWithProviders(
    <SelectColumnsStep
      newExp={{ task_name: "SomeTask", ...newExp }}
      setNewExp={setNewExp}
      setNextEnabled={setNextEnabled}
      dataset={{ id: 1 }}
      datasetInfo={{ column_names: ["a", "b", "c"] }}
      datasetTypes={{}}
      taskMetadata={SUPERVISED}
    />,
  );
  return { setNewExp, setNextEnabled };
};

const removeChip = (roleName, label) => {
  const root = document
    .querySelector(`#dataset-role-${roleName}-autocomplete`)
    .closest(".MuiAutocomplete-root");
  const chip = within(root).getByText(label).closest(".MuiChip-root");
  fireEvent.click(chip.querySelector(".MuiChip-deleteIcon"));
};

const addOption = (roleName, label) => {
  const root = document
    .querySelector(`#dataset-role-${roleName}-autocomplete`)
    .closest(".MuiAutocomplete-root");
  fireEvent.mouseDown(within(root).getByRole("combobox"));
  fireEvent.click(screen.getByRole("option", { name: label }));
};

describe("SelectColumnsStep, stage 2 of the wizard", () => {
  beforeEach(() => {
    getComponents.mockResolvedValue([]);
  });

  it("does not take a selection before the backend validated it", async () => {
    const first = deferred();
    const second = deferred();
    validateColumns
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const { setNewExp, setNextEnabled } = renderSelect();
    first.resolve({ dataset_status: "valid" });
    await waitFor(() => expect(setNextEnabled).toHaveBeenLastCalledWith(true));
    setNewExp.mockClear();

    removeChip("features", "b");

    await waitFor(() => expect(validateColumns).toHaveBeenCalledTimes(2));
    expect(setNextEnabled).toHaveBeenLastCalledWith(false);
    expect(setNewExp).not.toHaveBeenCalled();
  });

  it("keeps the answer to the latest selection, not the last to arrive", async () => {
    const answers = [deferred(), deferred(), deferred()];
    answers.forEach((answer) =>
      validateColumns.mockReturnValueOnce(answer.promise),
    );
    const { setNextEnabled } = renderSelect();
    answers[0].resolve({ dataset_status: "valid" });
    await waitFor(() => expect(setNextEnabled).toHaveBeenLastCalledWith(true));

    removeChip("features", "b");
    await waitFor(() => expect(validateColumns).toHaveBeenCalledTimes(2));
    addOption("features", "b");
    await waitFor(() => expect(validateColumns).toHaveBeenCalledTimes(3));
    answers[2].resolve({ dataset_status: "valid" });
    await waitFor(() => expect(setNextEnabled).toHaveBeenLastCalledWith(true));
    answers[1].resolve({ dataset_status: "invalid", error: "stale" });

    await new Promise((r) => setTimeout(r, 50));
    expect(setNextEnabled).toHaveBeenLastCalledWith(true);
    expect(screen.queryByText("stale")).not.toBeInTheDocument();
  });

  it("says so when the preprocessing result cannot be estimated", async () => {
    validateColumns.mockResolvedValue({ dataset_status: "valid" });
    getPreprocessingStructure.mockRejectedValue(new Error("500"));

    renderSelect({
      applyPreprocessing: true,
      column_roles_stage1: { features: ["a"], target: ["c"] },
      preprocessing: [{ converter: "Binarizer", params: {}, scope: [] }],
    });

    expect(
      await screen.findByText("Could not estimate the preprocessing result."),
    ).toBeInTheDocument();
  });

  it("drops a converter output picked for a chain that has changed since", async () => {
    validateColumns.mockResolvedValue({ dataset_status: "valid" });
    getPreprocessingStructure.mockResolvedValue({
      valid: true,
      final: [
        { kind: "column", name: "a", type: "Float", origin: null },
        { kind: "column", name: "b", type: "Float", origin: null },
        { kind: "block", step: 0, count: 2, type: "Float", slot: null },
      ],
    });
    const oneHot = {
      converter: "OneHotEncoder",
      params: {},
      scope: [raw("a")],
    };
    const pca = { converter: "PCA", params: {}, scope: [raw("a")] };

    renderSelect({
      applyPreprocessing: true,
      column_roles_stage1: { features: ["a", "b"], target: ["c"] },
      // Picked when step 0 was a one-hot encoder; it is a PCA now, and the
      // group key of its output is the same.
      column_roles: {
        features: [raw("b"), { kind: "group", step: 0 }],
        target: [raw("c")],
      },
      column_roles_steps: [oneHot],
      preprocessing: [pca],
    });

    await waitFor(() =>
      expect(validateColumns.mock.calls.at(-1)?.[2]).toEqual({
        features: [raw("b")],
        target: [raw("c")],
      }),
    );
  });
});

describe("RoleColumnSelectors, the maximum of a role", () => {
  const selectors = (roles, selection, onChange) =>
    renderWithProviders(
      <RoleColumnSelectors
        roles={roles}
        selection={selection}
        onChange={onChange}
        optionsFor={() => ["a", "b", "c"]}
        columnTypes={{}}
      />,
    );

  it("replaces, in sight, the column of a role that takes one", () => {
    const onChange = jest.fn();
    selectors(
      [role("target", "Target", { min: 1, max: 1 })],
      { target: ["a"] },
      onChange,
    );

    fireEvent.mouseDown(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("option", { name: "b" }));

    expect(onChange).toHaveBeenLastCalledWith("target", ["b"]);
  });

  it("does not offer more columns once a role has its maximum", () => {
    selectors(
      [role("pair", "Pair", { max: 2 })],
      { pair: ["a", "b"] },
      jest.fn(),
    );

    fireEvent.mouseDown(screen.getByRole("combobox"));

    expect(screen.getByRole("option", { name: "c" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });
});
