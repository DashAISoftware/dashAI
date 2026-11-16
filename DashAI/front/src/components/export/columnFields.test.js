import {
  COLUMN_FIELD_KEY,
  columnFieldParam,
  getColumnFields,
  isColumnFieldFilled,
} from "./columnFields";

const SCHEMA = {
  properties: {
    name: { type: "string", title: "Name" },
    label_column: {
      type: "string",
      title: "Label column",
      description: "Column to predict.",
      [COLUMN_FIELD_KEY]: "single",
    },
    skipped_columns: {
      anyOf: [{ type: "array", items: { type: "string" } }, { type: "null" }],
      title: "Skipped columns",
      [COLUMN_FIELD_KEY]: "multiple",
    },
  },
  required: ["name", "label_column", "skipped_columns"],
};

describe("getColumnFields", () => {
  it("lists only the fields the schema marks as column fields", () => {
    expect(getColumnFields(SCHEMA)).toEqual([
      {
        key: "label_column",
        title: "Label column",
        description: "Column to predict.",
        multiple: false,
        required: true,
      },
      {
        key: "skipped_columns",
        title: "Skipped columns",
        description: "",
        multiple: true,
        // Required by the schema, but it accepts null, so it may stay empty.
        required: false,
      },
    ]);
  });

  it("returns nothing for a missing schema or one without column fields", () => {
    expect(getColumnFields(null)).toEqual([]);
    expect(
      getColumnFields({ properties: { name: { type: "string" } } }),
    ).toEqual([]);
  });
});

describe("column field values", () => {
  const [single, multiple] = getColumnFields(SCHEMA);

  it("tells whether a value was picked", () => {
    expect(isColumnFieldFilled(single, "price")).toBe(true);
    expect(isColumnFieldFilled(single, "")).toBe(false);
    expect(isColumnFieldFilled(multiple, ["id"])).toBe(true);
    expect(isColumnFieldFilled(multiple, [])).toBe(false);
  });

  it("sends no columns of a list field as null", () => {
    expect(columnFieldParam(multiple, [])).toBeNull();
    expect(columnFieldParam(multiple, undefined)).toBeNull();
    expect(columnFieldParam(multiple, ["id"])).toEqual(["id"]);
    expect(columnFieldParam(single, undefined)).toBe("");
    expect(columnFieldParam(single, "price")).toBe("price");
  });
});
