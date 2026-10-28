import { mergeUnseen } from "./UnseenCategoriesAlert";

const record = (source, column, values, count = values.length) => ({
  source,
  column,
  values,
  count,
});

describe("mergeUnseen", () => {
  it("joins the records of several predictions by what treated which column", () => {
    const merged = mergeUnseen([
      {
        unseen_categories: [
          record("OneHotEncoder (step 1)", "color", ["teal"]),
        ],
      },
      { unseen_categories: null },
      {
        unseen_categories: [
          record("OneHotEncoder (step 1)", "color", ["purple", "teal"]),
          record("Forest (model)", "city", ["x"]),
        ],
      },
    ]);

    expect(merged).toEqual([
      record("OneHotEncoder (step 1)", "color", ["purple", "teal"]),
      record("Forest (model)", "city", ["x"]),
    ]);
  });

  it("keeps the largest count when a record only listed a sample", () => {
    const merged = mergeUnseen([
      { unseen_categories: [record("S", "c", ["a", "b"], 30)] },
      { unseen_categories: [record("S", "c", ["c"])] },
    ]);

    expect(merged).toEqual([record("S", "c", ["a", "b", "c"], 30)]);
  });

  it("gives nothing for predictions without records", () => {
    expect(mergeUnseen([{}, { unseen_categories: [] }])).toEqual([]);
  });
});
