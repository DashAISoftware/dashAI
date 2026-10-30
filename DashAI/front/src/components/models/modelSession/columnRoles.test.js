import {
  defaultRoleSelection,
  optionsForRole,
  rawRefs,
  resolveSelection,
  selectionReady,
  selectionToRefs,
  columnsByRole,
  sessionColumns,
  shownRoles,
} from "./columnRoles";

const FEATURES = {
  name: "features",
  label: "Features",
  min: 0,
  max: "n",
  required: false,
  transformable: true,
};
const TARGET = {
  name: "target",
  label: "Target",
  min: 1,
  max: 1,
  required: true,
  transformable: false,
};
const NO_TARGET = { ...TARGET, min: 0, max: 0, required: false };
const SUPERVISED = {
  column_roles: [FEATURES, TARGET],
  io_roles: { inputs: ["features"], outputs: ["target"] },
};
// A task with roles of its own: one date index and one series, both
// protected, and any number of exogenous columns.
const INDEX = { ...TARGET, name: "index", label: "Index" };
const SERIES = { ...TARGET, name: "series", label: "Series" };
const EXOGENOUS = { ...FEATURES, name: "exogenous", label: "Exogenous" };

describe("rawRefs", () => {
  test("turns column names into raw refs", () => {
    expect(rawRefs(["a", "b"])).toEqual([
      { kind: "raw", name: "a" },
      { kind: "raw", name: "b" },
    ]);
  });
});

describe("shownRoles", () => {
  test("hides a role that takes no columns", () => {
    expect(
      shownRoles({ column_roles: [FEATURES, NO_TARGET] }).map((r) => r.name),
    ).toEqual(["features"]);
  });

  test("shows nothing without the task's declaration", () => {
    expect(shownRoles(undefined)).toEqual([]);
  });
});

describe("defaultRoleSelection", () => {
  test("a supervised task: the last column is the target", () => {
    expect(defaultRoleSelection([FEATURES, TARGET], ["a", "b", "c"])).toEqual({
      features: ["a", "b"],
      target: ["c"],
    });
  });

  test("a task without a target: every column is a feature", () => {
    expect(defaultRoleSelection([FEATURES], ["a", "b"])).toEqual({
      features: ["a", "b"],
    });
  });

  test("protected roles take columns from the end, in declared order", () => {
    expect(
      defaultRoleSelection([INDEX, SERIES, EXOGENOUS], ["x", "d", "y"]),
    ).toEqual({ index: ["y"], series: ["d"], exogenous: ["x"] });
  });
});

describe("selectionReady", () => {
  test("needs every required role and some transformable column", () => {
    const roles = [FEATURES, TARGET];
    expect(selectionReady(roles, { features: ["a"], target: ["b"] })).toBe(
      true,
    );
    expect(selectionReady(roles, { features: ["a"], target: [] })).toBe(false);
    expect(selectionReady(roles, { features: [], target: ["b"] })).toBe(false);
  });

  test("a task whose only transformable role is optional and empty", () => {
    const roles = [INDEX, SERIES, EXOGENOUS];
    expect(selectionReady(roles, { index: ["d"], series: ["y"] })).toBe(false);
  });
});

describe("optionsForRole and resolveSelection", () => {
  const roles = [FEATURES, TARGET];
  const options = ["a", "b", "c"];

  test("a feature cannot take the target, the target can take a feature", () => {
    const selection = { features: ["a", "b"], target: ["c"] };
    expect(optionsForRole(FEATURES, options, selection, roles)).toEqual([
      "a",
      "b",
    ]);
    expect(optionsForRole(TARGET, options, selection, roles)).toEqual(options);
  });

  test("a column held by two roles stays with the protected one", () => {
    expect(
      resolveSelection(roles, { features: ["a", "b"], target: ["b"] }),
    ).toEqual({ features: ["a"], target: ["b"] });
  });
});

describe("selectionToRefs", () => {
  test("turns option keys into refs and leaves out empty roles", () => {
    expect(
      selectionToRefs({ features: ["a", "__group__0"], target: [] }),
    ).toEqual({
      features: [
        { kind: "raw", name: "a" },
        { kind: "group", step: 0 },
      ],
    });
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
    preprocessing: {
      steps: [
        {
          converter: "Binarizer",
          params: {},
          scope: [{ kind: "raw", name: "SepalLengthCm" }],
        },
      ],
    },
  };

  test("reads the model's inputs and outputs through the task's io_roles", () => {
    expect(sessionColumns(session, SUPERVISED)).toEqual({
      inputs: ["SepalWidthCm", "bin_SepalLengthCm"],
      inputRefs: session.column_roles.features.refs,
      rawInputs: ["SepalWidthCm", "SepalLengthCm"],
      outputs: ["Species"],
      target: "Species",
    });
  });

  test("with steps, the dataset columns are what the steps read, as in the backend", () => {
    // session_raw_columns decides by the steps, not by the refs: refs are
    // the only source of truth, and a role with columns but no refs feeds
    // the model nothing the backend would ask a dataset for.
    const withoutRefs = {
      ...session,
      column_roles: {
        ...session.column_roles,
        features: {
          refs: [],
          columns: ["SepalWidthCm", "bin_SepalLengthCm"],
        },
      },
    };

    expect(sessionColumns(withoutRefs, SUPERVISED).rawInputs).toEqual([
      "SepalLengthCm",
    ]);
  });

  test("a session without a target has no target column", () => {
    const clustering = {
      column_roles: { features: { refs: [], columns: ["hours", "score"] } },
    };

    expect(sessionColumns(clustering, SUPERVISED)).toEqual({
      inputs: ["hours", "score"],
      inputRefs: [],
      rawInputs: ["hours", "score"],
      outputs: [],
      target: undefined,
    });
  });

  test("reads nothing without the task's declaration", () => {
    expect(sessionColumns(session, {})).toEqual({
      inputs: [],
      inputRefs: [],
      rawInputs: [],
      outputs: [],
      target: undefined,
    });
  });
});

describe("defaultRoleSelection, by the types the roles declare", () => {
  const typed = (role, types) => ({ ...role, types });
  const TYPES = {
    date: { type: "Date" },
    promo: { type: "Float" },
    sales: { type: "Float" },
    label: { type: "Categorical" },
    width: { type: "Float" },
  };

  test("a protected role takes, from the end, the last column of a type it accepts", () => {
    expect(
      defaultRoleSelection(
        [
          typed(INDEX, ["Date"]),
          typed(SERIES, ["Float", "Integer"]),
          typed(EXOGENOUS, ["Float", "Integer"]),
        ],
        ["date", "promo", "sales"],
        TYPES,
      ),
    ).toEqual({ index: ["date"], series: ["sales"], exogenous: ["promo"] });
  });

  test("an x/y target that is not the last column is found by its type", () => {
    expect(
      defaultRoleSelection(
        [
          typed(FEATURES, ["Float", "Integer", "Categorical"]),
          typed(TARGET, ["Categorical"]),
        ],
        ["sales", "label", "width"],
        TYPES,
      ),
    ).toEqual({ features: ["sales", "width"], target: ["label"] });
  });

  test("an x/y target that is the last column stays the last column", () => {
    expect(
      defaultRoleSelection(
        [typed(FEATURES, ["Float"]), typed(TARGET, ["Categorical"])],
        ["sales", "width", "label"],
        TYPES,
      ),
    ).toEqual({ features: ["sales", "width"], target: ["label"] });
  });

  test("no column of an accepted type: the last one, as without types", () => {
    expect(
      defaultRoleSelection(
        [typed(FEATURES, ["Float"]), typed(TARGET, ["Categorical"])],
        ["sales", "width"],
        TYPES,
      ),
    ).toEqual({ features: ["sales"], target: ["width"] });
  });
});

describe("columnsByRole", () => {
  test("each role the task declares with the columns the session gave it, labelled as the task labels it", () => {
    const session = {
      column_roles: {
        target: { columns: ["Species"] },
        features: { columns: ["a", "b"] },
      },
    };

    expect(columnsByRole(session, SUPERVISED)).toEqual([
      { name: "features", label: "Features", columns: ["a", "b"] },
      { name: "target", label: "Target", columns: ["Species"] },
    ]);
  });

  test("a task with roles of its own: no input nor output, its roles", () => {
    const session = {
      column_roles: {
        index: { columns: ["date"] },
        series: { columns: ["sales"] },
      },
    };

    expect(
      columnsByRole(session, { column_roles: [INDEX, SERIES, EXOGENOUS] }),
    ).toEqual([
      { name: "index", label: "Index", columns: ["date"] },
      { name: "series", label: "Series", columns: ["sales"] },
    ]);
  });

  test("nothing without the task's declaration", () => {
    expect(columnsByRole({ column_roles: {} }, undefined)).toEqual([]);
  });
});
