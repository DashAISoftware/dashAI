import { isCompositeTreeComplete } from "./compositeTreeValidity";

const childrenSchema = (extra = {}) => ({
  properties: {
    retrievers: {
      type: "array",
      items: { type: "object", parent: "BaseRetriever" },
      ...extra,
    },
  },
});

const REGISTRY = {
  Dense: { schema: { properties: { top_k: { type: "integer" } } } },
  Sequential: { schema: childrenSchema() },
  Pair: { schema: childrenSchema({ minItems: 2 }) },
};
const find = (name) => REGISTRY[name] ?? null;

describe("isCompositeTreeComplete", () => {
  it("accepts a component that is not a container", () => {
    expect(
      isCompositeTreeComplete({ component: "Dense", params: {} }, find),
    ).toBe(true);
  });

  it("rejects a composite without children", () => {
    const ref = { component: "Sequential", params: { retrievers: [] } };
    expect(isCompositeTreeComplete(ref, find)).toBe(false);
  });

  it("rejects a composite whose children key is missing", () => {
    expect(
      isCompositeTreeComplete({ component: "Sequential", params: {} }, find),
    ).toBe(false);
  });

  it("accepts a composite with a configured child", () => {
    const ref = {
      component: "Sequential",
      params: { retrievers: [{ component: "Dense", params: {} }] },
    };
    expect(isCompositeTreeComplete(ref, find)).toBe(true);
  });

  it("ignores children that were added but never configured", () => {
    const ref = {
      component: "Sequential",
      params: { retrievers: [{ component: "", params: {} }] },
    };
    expect(isCompositeTreeComplete(ref, find)).toBe(false);
  });

  it("rejects a nested composite that is empty", () => {
    const ref = {
      component: "Sequential",
      params: {
        retrievers: [{ component: "Sequential", params: { retrievers: [] } }],
      },
    };
    expect(isCompositeTreeComplete(ref, find)).toBe(false);
  });

  it("honours the minimum number of children the schema declares", () => {
    const one = {
      component: "Pair",
      params: { retrievers: [{ component: "Dense", params: {} }] },
    };
    expect(isCompositeTreeComplete(one, find)).toBe(false);
    const two = {
      component: "Pair",
      params: {
        retrievers: [
          { component: "Dense", params: {} },
          { component: "Dense", params: {} },
        ],
      },
    };
    expect(isCompositeTreeComplete(two, find)).toBe(true);
  });

  it("rejects an unknown component", () => {
    expect(
      isCompositeTreeComplete({ component: "Nope", params: {} }, find),
    ).toBe(false);
  });
});
