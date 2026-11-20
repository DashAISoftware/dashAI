import {
  buildNodeFromRef,
  createIdFactory,
  findChildrenField,
  findParentNode,
  selectableOptions,
  serializeNode,
} from "./componentTreeUtils";

const listOf = (parent, extra = {}) => ({
  type: "array",
  items: { parent, type: "object" },
  ...extra,
});

const CONTAINER = {
  name: "Container",
  schema: {
    properties: { kids: listOf("Leafable", { minItems: 1, maxItems: 2 }) },
  },
};
const LEAF = {
  name: "Leaf",
  schema: { properties: { size: { type: "integer" } } },
};
const CATALOG = { Container: CONTAINER, Leaf: LEAF };
const find = (name) => CATALOG[name] ?? null;

describe("findChildrenField", () => {
  it("reads the key, the item parent and the size limits from the schema", () => {
    expect(findChildrenField(CONTAINER.schema)).toEqual({
      key: "kids",
      parent: "Leafable",
      minItems: 1,
      maxItems: 2,
    });
  });

  it("reads an optional array wrapped in anyOf", () => {
    const schema = {
      properties: { items: { anyOf: [listOf("Leafable"), { type: "null" }] } },
    };

    expect(findChildrenField(schema)).toMatchObject({
      key: "items",
      parent: "Leafable",
      maxItems: null,
    });
  });

  it("ignores arrays whose items are not components", () => {
    const schema = {
      properties: { tags: { type: "array", items: { type: "string" } } },
    };

    expect(findChildrenField(schema)).toBeNull();
  });

  it("returns null for a component without a schema", () => {
    expect(findChildrenField(undefined)).toBeNull();
  });
});

describe("buildNodeFromRef and serializeNode", () => {
  it("round-trips a nested ref under its own children key", () => {
    const ref = {
      component: "Container",
      params: { kids: [{ component: "Leaf", params: { size: 3 } }], other: 1 },
    };

    const node = buildNodeFromRef(ref, find, createIdFactory());

    expect(node.children).toHaveLength(1);
    expect(serializeNode(node, find)).toEqual(ref);
  });

  it("reads the legacy shape that kept children next to params", () => {
    const ref = {
      component: "Container",
      params: {},
      kids: [{ component: "Leaf", params: {} }],
    };

    const node = buildNodeFromRef(ref, find, createIdFactory());

    expect(node.children.map((child) => child.component)).toEqual(["Leaf"]);
  });

  it("drops unknown components and malformed refs", () => {
    const ref = {
      component: "Container",
      params: { kids: [{ component: "Ghost", params: {} }, "not a ref"] },
    };

    const node = buildNodeFromRef(ref, find, createIdFactory());

    expect(node.children).toEqual([]);
    expect(
      buildNodeFromRef({ component: "Ghost" }, find, createIdFactory()),
    ).toBeNull();
  });

  it("does not add a children key to a component that is not a container", () => {
    const node = buildNodeFromRef(
      { component: "Leaf", params: { size: 1 } },
      find,
      createIdFactory(),
    );

    expect(serializeNode(node, find)).toEqual({
      component: "Leaf",
      params: { size: 1 },
    });
  });
});

describe("findParentNode", () => {
  it("finds the container of a nested node and none for the root", () => {
    const ref = {
      component: "Container",
      params: { kids: [{ component: "Leaf", params: {} }] },
    };
    const root = buildNodeFromRef(ref, find, createIdFactory());

    expect(findParentNode(root, root.children[0].nodeId)).toBe(root);
    expect(findParentNode(root, root.nodeId)).toBeNull();
  });
});

describe("selectableOptions", () => {
  it("keeps configurable components once and groups them by category", () => {
    const options = selectableOptions(
      [
        { name: "A", metadata: { category: "x" } },
        { name: "B", metadata: { category: "y" } },
        { name: "C", metadata: { category: "x" } },
        { name: "A", metadata: { category: "x" } },
        { name: "Hidden", configurable_object: false },
      ],
      "other",
    );

    expect(options.map((option) => option.name)).toEqual(["A", "C", "B"]);
  });
});
