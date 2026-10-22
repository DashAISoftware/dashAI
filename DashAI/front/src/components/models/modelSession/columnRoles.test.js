import { rawRefs, rolesFromIo } from "./columnRoles";

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
