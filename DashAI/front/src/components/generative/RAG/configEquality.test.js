import fs from "fs";
import path from "path";

import {
  NO_IGNORED_KEYS,
  assertConfigurationValue,
  deepEqual,
} from "./configEquality";

const SHARED_CASES_PATH = path.resolve(
  __dirname,
  "../../../../../../tests/shared/config_equality_cases.json",
);

const SHARED_DATA = JSON.parse(fs.readFileSync(SHARED_CASES_PATH, "utf8"));
const SHARED_CASES = SHARED_DATA.cases;
const SHARED_MALFORMED_CASES = SHARED_DATA.malformed_cases ?? [];

describe("shared configuration equality cases", () => {
  test("the shared cases file resolves and is not empty", () => {
    expect(SHARED_CASES.length).toBeGreaterThan(0);
  });

  test.each(SHARED_CASES.map((c) => [c.name, c]))(
    "%s",
    (_name, { a, b, ignored_keys: ignoredKeys, equal }) => {
      expect(deepEqual(a, b, ignoredKeys)).toBe(equal);
      expect(deepEqual(b, a, ignoredKeys)).toBe(equal);
    },
  );

  test("every shared malformed case throws in both argument orders", () => {
    for (const { a, b, ignored_keys: ignoredKeys } of SHARED_MALFORMED_CASES) {
      expect(() => deepEqual(a, b, ignoredKeys)).toThrow();
      expect(() => deepEqual(b, a, ignoredKeys)).toThrow();
    }
  });
});

describe("deepEqual", () => {
  test("ignores object key order", () => {
    expect(
      deepEqual({ a: 1, b: { c: 2, d: 3 } }, { b: { d: 3, c: 2 }, a: 1 }),
    ).toBe(true);
  });

  test("compares arrays in order", () => {
    expect(deepEqual([1, 2, 3], [1, 2, 3])).toBe(true);
    expect(deepEqual([1, 2, 3], [3, 2, 1])).toBe(false);
    expect(deepEqual([1, 2], [1, 2, 3])).toBe(false);
  });

  test("compares nested structures", () => {
    expect(deepEqual({ x: [{ y: 1 }] }, { x: [{ y: 1 }] })).toBe(true);
    expect(deepEqual({ x: [{ y: 1 }] }, { x: [{ y: 2 }] })).toBe(false);
  });

  test("treats a key missing on one side as a difference", () => {
    expect(deepEqual({ a: 1, b: 2 }, { a: 1 })).toBe(false);
    expect(deepEqual({ a: 1 }, { a: 1, b: 2 })).toBe(false);
  });

  test("treats a key set to undefined the same as an absent key", () => {
    expect(deepEqual({ a: 1 }, { a: 1, b: undefined })).toBe(true);
    expect(deepEqual({ a: 1, b: undefined }, { a: 1 })).toBe(true);
    expect(deepEqual({ a: 1, b: undefined }, { a: 1, c: undefined })).toBe(
      true,
    );
  });

  test("treats a nested key set to undefined the same as an absent key", () => {
    expect(deepEqual({ x: { y: 1, z: undefined } }, { x: { y: 1 } })).toBe(
      true,
    );
    expect(
      deepEqual(
        { children: [{ component: "A", params: { k: undefined } }] },
        { children: [{ component: "A", params: {} }] },
      ),
    ).toBe(true);
  });

  test("does not treat null as an absent key", () => {
    expect(deepEqual({ a: 1, b: null }, { a: 1 })).toBe(false);
    expect(deepEqual({ a: 1 }, { a: 1, b: null })).toBe(false);
    expect(deepEqual({ a: null }, { a: undefined })).toBe(false);
  });

  test("compares null and primitives by strict type", () => {
    expect(deepEqual(null, null)).toBe(true);
    expect(deepEqual(null, {})).toBe(false);
    expect(deepEqual({}, null)).toBe(false);
    expect(deepEqual(5, 5)).toBe(true);
    expect(deepEqual(1, 1.0)).toBe(true);
    expect(deepEqual(-0, 0)).toBe(true);
    expect(deepEqual(0, false)).toBe(false);
    expect(deepEqual(false, null)).toBe(false);
    expect(deepEqual("5", 5)).toBe(false);
    expect(deepEqual("true", true)).toBe(false);
  });

  test("does not treat an array as an object with index keys", () => {
    expect(deepEqual([1], { 0: 1 })).toBe(false);
    expect(deepEqual({ 0: 1 }, [1])).toBe(false);
  });

  test("defaults to ignoring no keys", () => {
    expect(deepEqual({ top_k: 5 }, { top_k: 3 })).toBe(false);
    expect(deepEqual({ top_k: 5 }, { top_k: 3 }, NO_IGNORED_KEYS)).toBe(false);
  });

  test("ignores the given keys at every level, including inside arrays", () => {
    const left = { top_k: 5, children: [{ top_k: 1, x: { top_k: 9 } }] };
    const right = { top_k: 2, children: [{ top_k: 7, x: { top_k: 0 } }] };
    expect(deepEqual(left, right, ["top_k"])).toBe(true);
    expect(deepEqual(left, right, [])).toBe(false);
  });

  test("does not mutate its arguments", () => {
    const left = { a: 1, b: undefined, c: { d: [1, { e: 2 }] } };
    const right = { c: { d: [1, { e: 2 }] }, a: 1 };
    const ignored = ["zzz"];
    deepEqual(left, right, ignored);
    expect(Object.keys(left)).toEqual(["a", "b", "c"]);
    expect(ignored).toEqual(["zzz"]);
  });

  test("compares a key named __proto__ as ordinary data", () => {
    const left = JSON.parse('{"__proto__": 1}');
    expect(deepEqual(left, JSON.parse('{"__proto__": 1}'))).toBe(true);
    expect(deepEqual(left, {})).toBe(false);
  });

  test("accepts null-prototype objects as plain objects", () => {
    const left = Object.assign(Object.create(null), { a: 1 });
    expect(deepEqual(left, { a: 1 })).toBe(true);
  });
});

describe("deepEqual ignoredKeys validation", () => {
  test("throws when ignoredKeys is a bare string", () => {
    expect(() => deepEqual({ top_k: 1 }, {}, "top_k")).toThrow(
      "ignoredKeys must be an array of key names",
    );
  });

  test("throws when ignoredKeys holds a non-string", () => {
    expect(() => deepEqual({}, {}, [1])).toThrow(
      "ignored key names must be strings",
    );
  });

  test("throws when ignoredKeys is not an array", () => {
    expect(() => deepEqual({}, {}, { top_k: true })).toThrow(
      "ignoredKeys must be an array of key names",
    );
  });
});

describe("deepEqual malformed values", () => {
  test.each([
    ["a function", () => 1],
    ["a symbol", Symbol("x")],
    ["a bigint", BigInt(1)],
    ["a Date", new Date(0)],
    ["a Map", new Map([["a", 1]])],
    ["a Set", new Set([1])],
    ["a class instance", new (class Thing {})()],
    ["NaN", NaN],
    ["Infinity", Infinity],
    ["-Infinity", -Infinity],
    ["undefined at the top level", undefined],
  ])("throws when the left argument is %s", (_label, value) => {
    expect(() => deepEqual(value, 1)).toThrow(Error);
  });

  test.each([
    ["a function", () => 1],
    ["a symbol", Symbol("x")],
    ["a bigint", BigInt(1)],
    ["a Date", new Date(0)],
    ["NaN", NaN],
    ["undefined at the top level", undefined],
  ])("throws when the right argument is %s", (_label, value) => {
    expect(() => deepEqual(1, value)).toThrow(Error);
  });

  test.each([
    ["a function", () => 1],
    ["a Map", new Map()],
    ["NaN", NaN],
    ["Infinity", Infinity],
    ["undefined", undefined],
  ])("throws when an array element is %s", (_label, value) => {
    expect(() => deepEqual([1, value], [1, 1])).toThrow(Error);
    expect(() => deepEqual([1, 1], [1, value])).toThrow(Error);
  });

  test("throws on a malformed value nested in an object", () => {
    expect(() => deepEqual({ a: { b: () => 1 } }, { a: { b: 1 } })).toThrow(
      "left.a.b",
    );
    expect(() => deepEqual({ a: { b: 1 } }, { a: { b: new Date(0) } })).toThrow(
      Error,
    );
  });

  test("throws on a malformed value inside an ignored key", () => {
    expect(() =>
      deepEqual({ top_k: () => 1 }, { top_k: 1 }, ["top_k"]),
    ).toThrow(Error);
  });

  test("a malformed value throws even when an earlier key already differs", () => {
    expect(() => deepEqual({ a: 1, z: () => 1 }, { a: 2, z: 1 }, [])).toThrow(
      Error,
    );
    expect(() => deepEqual([1, 2, NaN], [3, 2, 1])).toThrow(Error);
  });

  test("an array hole is malformed, on either side, not a skipped element", () => {
    const holed = [0, 1];
    delete holed[0];
    expect(() => deepEqual(holed, [2, 1])).toThrow("left[0]");
    expect(() => deepEqual([2, 1], holed)).toThrow("right[0]");
    expect(() => deepEqual({ items: holed }, { items: [2, 1] })).toThrow(
      "left.items[0]",
    );
  });

  test("a malformed value throws even when the arrays differ in length", () => {
    expect(() => deepEqual([1], [1, () => 1])).toThrow(Error);
  });

  test("an undefined object property counts as absent, on either side", () => {
    expect(deepEqual({ a: undefined }, {})).toBe(true);
    expect(deepEqual({}, { a: undefined })).toBe(true);
    expect(deepEqual({ a: undefined, b: 1 }, { b: 1 })).toBe(true);
  });

  test("an object property holding a function is malformed, not absent", () => {
    expect(() => deepEqual({ a: () => 1 }, {})).toThrow(Error);
    expect(() => deepEqual({}, { a: () => 1 })).toThrow(Error);
  });

  test("an object with a symbol key is malformed", () => {
    const withSymbol = { a: 1, [Symbol("k")]: 1 };
    expect(() => deepEqual(withSymbol, { a: 1 })).toThrow(Error);
  });

  test("a non-plain object inside an object is malformed", () => {
    expect(() => deepEqual({ when: new Date(0) }, { when: null })).toThrow(
      Error,
    );
  });
});

describe("deepEqual integer range", () => {
  test("accepts integers up to the safe bound on both sides", () => {
    expect(deepEqual(Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER)).toBe(
      true,
    );
    expect(deepEqual(-Number.MAX_SAFE_INTEGER, -Number.MAX_SAFE_INTEGER)).toBe(
      true,
    );
  });

  test.each([
    ["just above the safe bound", 2 ** 53],
    ["far above the safe bound", 2 ** 60],
    ["just below the negative bound", -(2 ** 53)],
  ])("throws for an integer %s, on either side", (_label, value) => {
    expect(() => deepEqual(value, 1)).toThrow("outside +/-(2^53-1)");
    expect(() => deepEqual(1, value)).toThrow("outside +/-(2^53-1)");
  });

  test("throws for an out-of-range integer nested in a configuration", () => {
    expect(() => deepEqual({ a: [2 ** 53] }, { a: [1] })).toThrow("left.a[0]");
  });

  test("non-integer floats are unaffected by the integer bound", () => {
    expect(deepEqual(0.5, 0.5)).toBe(true);
    expect(deepEqual(-1.25, -1.25)).toBe(true);
    expect(deepEqual(0.1, 0.2)).toBe(false);
  });
});

describe("assertConfigurationValue", () => {
  test("accepts a valid nested configuration", () => {
    expect(() =>
      assertConfigurationValue({ a: [1, { b: null, c: false }], d: undefined }),
    ).not.toThrow();
  });

  test("names the value in the error message", () => {
    expect(() =>
      assertConfigurationValue({ a: [() => 1] }, "ref.params"),
    ).toThrow("ref.params.a[0]");
  });

  test("throws on undefined at the top level", () => {
    expect(() => assertConfigurationValue(undefined)).toThrow(Error);
  });
});
