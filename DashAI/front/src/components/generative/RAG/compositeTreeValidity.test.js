import { isCompositeTreeComplete } from "./compositeTreeValidity";

const childrenSchema = (extra = {}) => ({
  properties: {
    children: {
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
  ScorerMMR: {
    schema: {
      properties: {
        children: {
          anyOf: [
            {
              type: "array",
              items: { type: "object", parent: "ChunkScorer" },
              minItems: 1,
            },
            { type: "null" },
          ],
        },
      },
    },
  },
};
const find = (name) => REGISTRY[name] ?? null;

describe("isCompositeTreeComplete", () => {
  it("accepts a component that is not a container", () => {
    expect(
      isCompositeTreeComplete({ component: "Dense", params: {} }, find),
    ).toBe(true);
  });

  it("rejects a composite without children", () => {
    const ref = { component: "Sequential", params: { children: [] } };
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
      params: { children: [{ component: "Dense", params: {} }] },
    };
    expect(isCompositeTreeComplete(ref, find)).toBe(true);
  });

  it("ignores children that were added but never configured", () => {
    const ref = {
      component: "Sequential",
      params: { children: [{ component: "", params: {} }] },
    };
    expect(isCompositeTreeComplete(ref, find)).toBe(false);
  });

  it("rejects a composite that keeps an unknown or unreadable child", () => {
    const withGhost = {
      component: "Sequential",
      params: {
        children: [
          { component: "Dense", params: {} },
          { component: "Ghost", params: {} },
        ],
      },
    };
    const withJunk = {
      component: "Sequential",
      params: { children: [{ component: "Dense", params: {} }, "junk"] },
    };
    expect(isCompositeTreeComplete(withGhost, find)).toBe(false);
    expect(isCompositeTreeComplete(withJunk, find)).toBe(false);
  });

  it("rejects a nested composite that is empty", () => {
    const ref = {
      component: "Sequential",
      params: {
        children: [{ component: "Sequential", params: { children: [] } }],
      },
    };
    expect(isCompositeTreeComplete(ref, find)).toBe(false);
  });

  it("honours the minimum number of children the schema declares", () => {
    const one = {
      component: "Pair",
      params: { children: [{ component: "Dense", params: {} }] },
    };
    expect(isCompositeTreeComplete(one, find)).toBe(false);
    const two = {
      component: "Pair",
      params: {
        children: [
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

  it("rejects a missing or empty reference", () => {
    expect(isCompositeTreeComplete(null, find)).toBe(false);
    expect(isCompositeTreeComplete(undefined, find)).toBe(false);
    expect(isCompositeTreeComplete({ component: "", params: {} }, find)).toBe(
      false,
    );
  });

  it("reads an optional children list declared through anyOf (a reranker)", () => {
    const empty = { component: "ScorerMMR", params: { children: [] } };
    const filled = {
      component: "ScorerMMR",
      params: { children: [{ component: "Dense", params: {} }] },
    };
    expect(isCompositeTreeComplete(empty, find)).toBe(false);
    expect(isCompositeTreeComplete(filled, find)).toBe(true);
  });

  it("rejects a reranker whose children key is null", () => {
    expect(
      isCompositeTreeComplete(
        { component: "ScorerMMR", params: { children: null } },
        find,
      ),
    ).toBe(false);
  });
});
