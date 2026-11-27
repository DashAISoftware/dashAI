import { NO_IGNORED_KEYS } from "./configEquality";
import {
  RETRIEVER_MATCH_IGNORED_KEYS,
  findMatchingPreset,
} from "./presetMatching";

const KEYWORD_PARAMS = {
  top_k: 5,
  vectorizer: "bag_of_words",
  enable_retrieve_then_expand: false,
  expand_window: 1,
};

const KEYWORD_PRESET = {
  key: "keyword",
  component: "BM25Retriever",
  params: KEYWORD_PARAMS,
};

const SEMANTIC_PRESET = {
  key: "semantic",
  component: "SemanticRetriever",
  params: { top_k: 5, batch_size: 32 },
};

/** A hybrid recipe: parent top_k plus two children, each with its own top_k. */
function hybridParams({
  parentTopK = 10,
  keywordTopK = 5,
  semanticTopK = 5,
  metric = "cosine",
} = {}) {
  return {
    top_k: parentTopK,
    children: [
      {
        component: "BM25Retriever",
        params: { top_k: keywordTopK, vectorizer: "bag_of_words" },
      },
      {
        component: "SemanticRetriever",
        params: { top_k: semanticTopK, similarity_metric: metric },
      },
    ],
  };
}

const HYBRID_PRESET = {
  key: "hybrid",
  component: "HybridRetriever",
  params: hybridParams(),
};

const ALL_PRESETS = [KEYWORD_PRESET, SEMANTIC_PRESET, HYBRID_PRESET];

describe("findMatchingPreset", () => {
  test("matches the same params in a different key order", () => {
    const ref = {
      component: "BM25Retriever",
      params: {
        expand_window: 1,
        enable_retrieve_then_expand: false,
        vectorizer: "bag_of_words",
        top_k: 5,
      },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBe(KEYWORD_PRESET);
  });

  test("still matches when only top_k differs on a flat retriever", () => {
    const ref = {
      component: "BM25Retriever",
      params: { ...KEYWORD_PARAMS, top_k: 12 },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBe(KEYWORD_PRESET);
  });

  test("still matches a hybrid whose parent and child top_k differ", () => {
    const ref = {
      component: "HybridRetriever",
      params: hybridParams({
        parentTopK: 20,
        keywordTopK: 1,
        semanticTopK: 19,
      }),
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBe(HYBRID_PRESET);
  });

  test("does not match a hybrid whose children are in a different order", () => {
    const params = hybridParams();
    const reordered = {
      ...params,
      children: [...params.children].reverse(),
    };
    expect(
      findMatchingPreset(
        { component: "HybridRetriever", params: reordered },
        ALL_PRESETS,
        RETRIEVER_MATCH_IGNORED_KEYS,
      ),
    ).toBeNull();
  });

  test("does not match when a child's similarity metric changes", () => {
    const ref = {
      component: "HybridRetriever",
      params: hybridParams({ metric: "dot" }),
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBeNull();
  });

  test("does not match when a child's component changes", () => {
    const params = hybridParams();
    params.children[1].component = "BM25Retriever";
    expect(
      findMatchingPreset(
        { component: "HybridRetriever", params },
        ALL_PRESETS,
        RETRIEVER_MATCH_IGNORED_KEYS,
      ),
    ).toBeNull();
  });

  test("does not match when a child reference has an extra key", () => {
    const params = hybridParams();
    params.children[0].extra = true;
    expect(
      findMatchingPreset(
        { component: "HybridRetriever", params },
        ALL_PRESETS,
        RETRIEVER_MATCH_IGNORED_KEYS,
      ),
    ).toBeNull();
  });

  test("matches when a key is set to undefined in place of being absent", () => {
    const ref = {
      component: "SemanticRetriever",
      params: { top_k: 5, batch_size: 32, extra: undefined },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBe(SEMANTIC_PRESET);
  });

  test("matches a nested child key set to undefined", () => {
    const params = hybridParams();
    params.children[0].params.extra = undefined;
    expect(
      findMatchingPreset(
        { component: "HybridRetriever", params },
        ALL_PRESETS,
        RETRIEVER_MATCH_IGNORED_KEYS,
      ),
    ).toBe(HYBRID_PRESET);
  });

  test("does not match when a param is null where the preset omits it", () => {
    const ref = {
      component: "SemanticRetriever",
      params: { top_k: 5, batch_size: 32, extra: null },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBeNull();
  });

  test("throws a clear error when ignoredKeys is omitted", () => {
    expect(() =>
      findMatchingPreset(
        { component: "BM25Retriever", params: {} },
        ALL_PRESETS,
      ),
    ).toThrow("ignoredKeys must be an array");
  });

  test("does not match when enable_retrieve_then_expand changes", () => {
    const ref = {
      component: "BM25Retriever",
      params: { ...KEYWORD_PARAMS, enable_retrieve_then_expand: true },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBeNull();
  });

  test("does not match when expand_window changes", () => {
    const ref = {
      component: "BM25Retriever",
      params: { ...KEYWORD_PARAMS, expand_window: 2 },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBeNull();
  });

  test("does not match when batch_size changes", () => {
    const ref = {
      component: "SemanticRetriever",
      params: { top_k: 5, batch_size: 64 },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBeNull();
  });

  test("does not match when a key is missing on one side", () => {
    const { expand_window: _dropped, ...withoutWindow } = KEYWORD_PARAMS;
    const ref = { component: "BM25Retriever", params: withoutWindow };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBeNull();
  });

  test("does not match a different component with identical params", () => {
    const ref = {
      component: "SemanticRetriever",
      params: { ...KEYWORD_PARAMS },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBeNull();
  });

  test("compares every parameter when no keys are ignored", () => {
    const ref = {
      component: "BM25Retriever",
      params: { ...KEYWORD_PARAMS, top_k: 12 },
    };
    expect(
      findMatchingPreset(ref, [KEYWORD_PRESET], NO_IGNORED_KEYS),
    ).toBeNull();
  });

  test("does not mutate the reference or the presets", () => {
    const ref = {
      component: "HybridRetriever",
      params: hybridParams({ parentTopK: 20 }),
    };
    const refSnapshot = JSON.parse(JSON.stringify(ref));
    const presetsSnapshot = JSON.parse(JSON.stringify(ALL_PRESETS));

    findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS);

    expect(ref).toEqual(refSnapshot);
    expect(ALL_PRESETS).toEqual(presetsSnapshot);
  });
});

describe("findMatchingPreset params comparison", () => {
  test("a boolean parameter does not match a numeric one", () => {
    const ref = {
      component: "BM25Retriever",
      params: { ...KEYWORD_PARAMS, enable_retrieve_then_expand: 0 },
    };
    expect(
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toBeNull();
  });

  test("a malformed param value throws even when the component is unknown", () => {
    const ref = {
      component: "Unknown",
      params: { top_k: 5, custom: () => 1 },
    };
    expect(() =>
      findMatchingPreset(ref, ALL_PRESETS, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toThrow(Error);
  });

  test("a malformed preset param throws even when its component differs", () => {
    const presets = [
      { key: "bad", component: "Other", params: { value: NaN } },
    ];
    expect(() =>
      findMatchingPreset(
        { component: "BM25Retriever", params: { top_k: 5 } },
        presets,
        RETRIEVER_MATCH_IGNORED_KEYS,
      ),
    ).toThrow(Error);
  });
});

describe("findMatchingPreset input validation", () => {
  const REF_ERROR = "must be a {component, params} object";
  const validRef = { component: "BM25Retriever", params: { top_k: 5 } };
  const match = (ref, presets = ALL_PRESETS) =>
    findMatchingPreset(ref, presets, RETRIEVER_MATCH_IGNORED_KEYS);

  test.each([
    ["null", null],
    ["undefined", undefined],
    ["a string", "BM25Retriever"],
    ["an array", [validRef]],
  ])("throws when ref is %s", (_label, ref) => {
    expect(() => match(ref)).toThrow(REF_ERROR);
  });

  test("throws when ref has no component", () => {
    expect(() => match({ params: { top_k: 5 } })).toThrow(REF_ERROR);
  });

  test("throws when ref has an empty component", () => {
    expect(() => match({ component: "", params: { top_k: 5 } })).toThrow(
      REF_ERROR,
    );
  });

  test.each([
    ["a number", 42],
    ["null", null],
    ["an object", { name: "BM25Retriever" }],
  ])("throws when ref component is %s", (_label, component) => {
    expect(() => match({ component, params: { top_k: 5 } })).toThrow(REF_ERROR);
  });

  test("throws when ref has no params, rather than treating it as empty", () => {
    expect(() => match({ component: "BM25Retriever" })).toThrow(REF_ERROR);
  });

  test.each([
    ["a string", "top_k"],
    ["an array", [5]],
    ["null", null],
    ["a number", 5],
  ])("throws when ref params is %s", (_label, params) => {
    expect(() => match({ component: "BM25Retriever", params })).toThrow(
      REF_ERROR,
    );
  });

  test("throws when the presets are not an array", () => {
    expect(() =>
      findMatchingPreset(validRef, undefined, RETRIEVER_MATCH_IGNORED_KEYS),
    ).toThrow("presets must be an array");
  });

  test("throws when a preset has no component", () => {
    const presets = [{ key: "bad", params: { top_k: 5 } }];
    expect(() => match(validRef, presets)).toThrow("presets[0] must be a");
  });

  test("throws when a preset has an empty component", () => {
    const presets = [KEYWORD_PRESET, { key: "bad", component: "", params: {} }];
    expect(() => match(validRef, presets)).toThrow("presets[1] must be a");
  });

  test("throws when a preset has no params", () => {
    const presets = [{ key: "bad", component: "BM25Retriever" }];
    expect(() => match(validRef, presets)).toThrow("presets[0] must be a");
  });

  test("throws when a preset has non-object params", () => {
    const presets = [{ key: "bad", component: "BM25Retriever", params: "x" }];
    expect(() => match(validRef, presets)).toThrow("presets[0] must be a");
  });

  test("throws when a preset entry is not an object", () => {
    expect(() => match(validRef, [null])).toThrow("presets[0] must be a");
  });

  test("a malformed preset throws even when an earlier preset matches", () => {
    const presets = [KEYWORD_PRESET, { key: "bad", component: 7, params: {} }];
    expect(() =>
      match({ ...validRef, params: KEYWORD_PARAMS }, presets),
    ).toThrow("presets[1] must be a");
  });

  test("a valid reference with no matching preset still returns null", () => {
    expect(match({ component: "Unknown", params: {} })).toBeNull();
    expect(match(validRef, [])).toBeNull();
  });
});
