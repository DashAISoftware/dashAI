import { rawRefs, rolesFromIo, sessionColumns } from "./columnRoles";

const SUPERVISED = { io_roles: { inputs: ["features"], outputs: ["target"] } };

describe("rawRefs", () => {
  test("turns column names into raw refs", () => {
    expect(rawRefs(["a", "b"])).toEqual([
      { kind: "raw", name: "a" },
      { kind: "raw", name: "b" },
    ]);
  });
});

describe("rolesFromIo", () => {
  test("puts the inputs and outputs under the roles the task declares", () => {
    const inputs = [{ kind: "group", step: 0 }];
    const outputs = rawRefs(["Species"]);

    expect(rolesFromIo(SUPERVISED, inputs, outputs)).toEqual({
      features: inputs,
      target: outputs,
    });
  });

  test("names roles only as the metadata does", () => {
    const metadata = {
      io_roles: { inputs: ["source"], outputs: ["translation"] },
    };

    expect(rolesFromIo(metadata, ["a"], ["b"])).toEqual({
      source: ["a"],
      translation: ["b"],
    });
  });

  test("leaves out a role given no columns", () => {
    expect(rolesFromIo(SUPERVISED, rawRefs(["x"]), [])).toEqual({
      features: [{ kind: "raw", name: "x" }],
    });
  });

  test("builds nothing without the task's declaration", () => {
    expect(rolesFromIo(undefined, ["a"], ["b"])).toEqual({});
  });
});

describe("sessionColumns", () => {
  const session = {
    task_name: "TabularClassificationTask",
    column_roles: {
      features: {
        refs: [
          { kind: "raw", name: "SepalWidthCm" },
          { kind: "group", step: 0, slot: null, name: null },
        ],
        columns: ["SepalWidthCm", "bin_SepalLengthCm"],
      },
      target: {
        refs: [{ kind: "raw", name: "Species" }],
        columns: ["Species"],
      },
    },
  };

  test("reads the model's inputs and outputs through the task's io_roles", () => {
    expect(sessionColumns(session, SUPERVISED)).toEqual({
      inputs: ["SepalWidthCm", "bin_SepalLengthCm"],
      inputRefs: session.column_roles.features.refs,
      outputs: ["Species"],
      target: "Species",
    });
  });

  test("a session without a target has no target column", () => {
    const clustering = {
      column_roles: { features: { refs: [], columns: ["hours", "score"] } },
    };

    expect(sessionColumns(clustering, SUPERVISED)).toEqual({
      inputs: ["hours", "score"],
      inputRefs: [],
      outputs: [],
      target: undefined,
    });
  });

  test("reads nothing without the task's declaration", () => {
    expect(sessionColumns(session, {})).toEqual({
      inputs: [],
      inputRefs: [],
      outputs: [],
      target: undefined,
    });
  });
});
