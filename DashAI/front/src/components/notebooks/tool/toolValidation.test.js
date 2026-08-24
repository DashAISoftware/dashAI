import { validateConverter } from "./toolValidation";

const t = (key, opts) => {
  if (key === "datasets:error.requiresExactColumns") {
    return `requires exactly ${opts.required}, got ${opts.available}`;
  }
  if (key === "datasets:error.requiresMinColumns") {
    return `requires at least ${opts.required}, got ${opts.available}`;
  }
  if (key === "datasets:error.noValidColumnsWithDtypesMentioned") {
    return `no columns match dtypes: ${opts.dtypes}`;
  }
  return key;
};

const numericColumn = {
  id: 0,
  columnName: "a",
  valueType: "Numerical",
  dataType: "float64",
};
const categoricalColumn = {
  id: 1,
  columnName: "b",
  valueType: "Categorical",
  dataType: "object",
};

describe("validateConverter", () => {
  it("is enabled with no restrictions and no dataset columns known yet", () => {
    const result = validateConverter({ metadata: {} }, [], t);
    expect(result).toEqual({ disabled: false, tooltip: "" });
  });

  it("disables when allowed_types excludes every available column", () => {
    const converter = {
      description: "desc",
      metadata: { allowed_types: ["Categorical"] },
    };
    const result = validateConverter(converter, [numericColumn], t);
    expect(result.disabled).toBe(true);
    expect(result.tooltip).toContain("no columns match dtypes: Categorical");
  });

  it("stays enabled when at least one column matches allowed_types", () => {
    const converter = {
      metadata: { allowed_types: ["Categorical"] },
    };
    const result = validateConverter(
      converter,
      [numericColumn, categoricalColumn],
      t,
    );
    expect(result.disabled).toBe(false);
    expect(result.validColumns).toEqual([categoricalColumn]);
  });

  it("disables when input_cardinality.exact is not met", () => {
    const converter = {
      metadata: { input_cardinality: { exact: 2 } },
    };
    const result = validateConverter(converter, [numericColumn], t);
    expect(result.disabled).toBe(true);
    expect(result.tooltip).toContain("requires exactly 2, got 1");
  });

  it("disables when input_cardinality.min is not met", () => {
    const converter = {
      metadata: { input_cardinality: { min: 3 } },
    };
    const result = validateConverter(
      converter,
      [numericColumn, categoricalColumn],
      t,
    );
    expect(result.disabled).toBe(true);
    expect(result.tooltip).toContain("requires at least 3, got 2");
  });
});
