import React from "react";
import { screen, waitFor, within } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import { getComponents } from "../../../api/component";
import {
  getPreprocessingStructure,
  validateColumns,
} from "../../../api/modelSession";

jest.mock("../../../api/component", () => ({
  getComponents: jest.fn(),
}));

jest.mock("../../../api/modelSession", () => ({
  getPreprocessingStructure: jest.fn(),
  validateColumns: jest.fn(),
}));

import BaseColumnsStep from "./BaseColumnsStep";
import SelectColumnsStep from "./SelectColumnsStep";

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
const PROTECTED = { min: 1, max: 1, required: true, transformable: false };

const SUPERVISED = {
  column_roles: [
    role("features", "Features"),
    role("target", "Target", { ...PROTECTED, types: ["Categorical"] }),
  ],
  io_roles: { inputs: ["features"], outputs: ["target"] },
};
// A task without outputs declares no target role at all.
const CLUSTERING = {
  column_roles: [role("features", "Features")],
  io_roles: { inputs: ["features"], outputs: [] },
};
// A task with roles of its own, as a forecasting task would declare them.
const THREE_ROLES = {
  column_roles: [
    role("index", "Index", { ...PROTECTED, types: ["Date"] }),
    role("series", "Series", PROTECTED),
    role("exogenous", "Exogenous"),
  ],
  io_roles: { inputs: ["exogenous"], outputs: ["series"] },
};

const COLUMNS = ["a", "b", "c"];

const selectorLabels = () =>
  screen
    .getAllByRole("combobox")
    .map((input) => input.closest(".MuiAutocomplete-root"))
    .map((root) =>
      root.querySelector("label").textContent.replace(/\s*\*$/, ""),
    );

const TYPES = {
  a: { type: "Float" },
  b: { type: "Integer" },
  c: { type: "Categorical" },
};

// The type badge next to the column a role holds, in its selector.
const heldType = (roleName, column) =>
  within(
    document
      .querySelector(`#dataset-role-${roleName}-autocomplete`)
      .closest(".MuiAutocomplete-root"),
  )
    .getByText(column)
    .closest(".MuiChip-root").textContent;

const renderSelect = (taskMetadata, newExp = {}, datasetTypes = {}) => {
  const setNewExp = jest.fn();
  const setNextEnabled = jest.fn();
  renderWithProviders(
    <SelectColumnsStep
      newExp={{ task_name: "SomeTask", ...newExp }}
      setNewExp={setNewExp}
      setNextEnabled={setNextEnabled}
      dataset={{ id: 1 }}
      datasetInfo={{ column_names: COLUMNS }}
      datasetTypes={datasetTypes}
      taskMetadata={taskMetadata}
    />,
  );
  return { setNewExp, setNextEnabled };
};

describe("SelectColumnsStep", () => {
  beforeEach(() => {
    getComponents.mockResolvedValue([]);
    validateColumns.mockResolvedValue({ dataset_status: "valid" });
    getPreprocessingStructure.mockResolvedValue({ final: [], valid: true });
  });

  it("shows one selector per role of a supervised task", async () => {
    renderSelect(SUPERVISED);
    await waitFor(() => expect(validateColumns).toHaveBeenCalled());

    expect(selectorLabels()).toEqual(["Features", "Target"]);
  });

  it("sends the default columns by role: the last one is the target", async () => {
    const { setNewExp } = renderSelect(SUPERVISED);

    await waitFor(() => expect(setNewExp).toHaveBeenCalled());
    expect(validateColumns).toHaveBeenCalledWith(
      "SomeTask",
      1,
      {
        features: [
          { kind: "raw", name: "a" },
          { kind: "raw", name: "b" },
        ],
        target: [{ kind: "raw", name: "c" }],
      },
      undefined,
    );
    expect(setNewExp.mock.calls.at(-1)[0].column_roles).toEqual({
      features: [
        { kind: "raw", name: "a" },
        { kind: "raw", name: "b" },
      ],
      target: [{ kind: "raw", name: "c" }],
    });
  });

  it("shows no selector for a role that takes no columns", async () => {
    renderSelect(CLUSTERING);
    await waitFor(() => expect(validateColumns).toHaveBeenCalled());

    expect(selectorLabels()).toEqual(["Features"]);
    expect(validateColumns.mock.calls.at(-1)[2]).toEqual({
      features: COLUMNS.map((name) => ({ kind: "raw", name })),
    });
  });

  it("shows the roles a task declares, without naming them", async () => {
    renderSelect(THREE_ROLES);
    await waitFor(() => expect(validateColumns).toHaveBeenCalled());

    expect(selectorLabels()).toEqual(["Index", "Series", "Exogenous"]);
    expect(validateColumns.mock.calls.at(-1)[2]).toEqual({
      index: [{ kind: "raw", name: "c" }],
      series: [{ kind: "raw", name: "b" }],
      exogenous: [{ kind: "raw", name: "a" }],
    });
  });

  it("keeps the tour anchors on the first input and output roles", async () => {
    renderSelect(SUPERVISED);
    await waitFor(() => expect(validateColumns).toHaveBeenCalled());

    const anchored = (anchor) =>
      document.querySelector(`[data-tour="${anchor}"] input`).id;
    expect(anchored("dataset-input-columns-autocomplete")).toBe(
      "dataset-role-features-autocomplete",
    );
    expect(anchored("dataset-output-columns-autocomplete")).toBe(
      "dataset-role-target-autocomplete",
    );
  });

  it("with preprocessing, a protected role keeps its columns and is fixed", async () => {
    getPreprocessingStructure.mockResolvedValue({
      valid: true,
      final: [
        { kind: "column", name: "a", type: "Float", origin: null },
        { kind: "column", name: "bin_a", type: "Integer", origin: 0 },
      ],
    });
    renderSelect(SUPERVISED, {
      applyPreprocessing: true,
      column_roles_stage1: { features: ["a"], target: ["c"] },
      preprocessing: [{ converter: "Binarizer", params: {}, scope: [] }],
    });

    await waitFor(() =>
      expect(validateColumns.mock.calls.at(-1)?.[2]).toEqual({
        features: [
          { kind: "raw", name: "a" },
          { kind: "group", step: 0, name: "bin_a" },
        ],
        target: [{ kind: "raw", name: "c" }],
      }),
    );
    expect(getPreprocessingStructure.mock.calls.at(-1)[0].columnRoles).toEqual({
      features: ["a"],
      target: ["c"],
    });
    const target = document.querySelector("#dataset-role-target-autocomplete");
    expect(target).toBeDisabled();
  });
  it("shows the type of the column every role that takes one holds", async () => {
    renderSelect(THREE_ROLES, {}, TYPES);
    await waitFor(() => expect(validateColumns).toHaveBeenCalled());

    expect(heldType("index", "c")).toBe("cCategorical");
    expect(heldType("series", "b")).toBe("bInteger");
  });

  it("with preprocessing, the fixed target still shows its type", async () => {
    getPreprocessingStructure.mockResolvedValue({
      valid: true,
      final: [{ kind: "column", name: "a", type: "Float", origin: null }],
    });
    renderSelect(
      SUPERVISED,
      {
        applyPreprocessing: true,
        column_roles_stage1: { features: ["a"], target: ["c"] },
        preprocessing: [{ converter: "Binarizer", params: {}, scope: [] }],
      },
      TYPES,
    );
    await waitFor(() => expect(validateColumns).toHaveBeenCalled());

    expect(heldType("target", "c")).toBe("cCategorical");
  });
});

describe("BaseColumnsStep", () => {
  it("gives candidates to the transformable roles and keeps the target", async () => {
    const setNewExp = jest.fn();
    const setNextEnabled = jest.fn();
    renderWithProviders(
      <BaseColumnsStep
        newExp={{}}
        setNewExp={setNewExp}
        setNextEnabled={setNextEnabled}
        datasetInfo={{ column_names: COLUMNS }}
        datasetTypes={{}}
        taskMetadata={SUPERVISED}
      />,
    );

    await waitFor(() => expect(setNextEnabled).toHaveBeenLastCalledWith(true));
    expect(selectorLabels()).toEqual([
      "Features (candidate columns)",
      "Target",
    ]);
    const update = setNewExp.mock.calls.at(-1)[0];
    expect(update({}).column_roles_stage1).toEqual({
      features: ["a", "b"],
      target: ["c"],
    });
  });

  it("shows the type of the column the target holds", async () => {
    const setNextEnabled = jest.fn();
    renderWithProviders(
      <BaseColumnsStep
        newExp={{}}
        setNewExp={jest.fn()}
        setNextEnabled={setNextEnabled}
        datasetInfo={{ column_names: COLUMNS }}
        datasetTypes={TYPES}
        taskMetadata={SUPERVISED}
      />,
    );

    await waitFor(() => expect(setNextEnabled).toHaveBeenLastCalledWith(true));
    expect(heldType("target", "c")).toBe("cCategorical");
  });
});
