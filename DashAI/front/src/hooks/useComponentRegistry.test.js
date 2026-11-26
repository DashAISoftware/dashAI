import { renderHook, waitFor } from "@testing-library/react";
import useComponentRegistry from "./useComponentRegistry";
import { getChildComponents } from "../api/component";

jest.mock("../api/component", () => ({ getChildComponents: jest.fn() }));

const listOf = (parent) => ({
  type: "array",
  items: { type: "object", parent },
});

const CATALOG = {
  Root: [
    {
      name: "Container",
      schema: { properties: { children: listOf("Leafable") } },
    },
    { name: "Leaf", schema: { properties: {} } },
  ],
  Leafable: [{ name: "Leaf", schema: { properties: {} } }],
};

beforeEach(() => {
  getChildComponents.mockReset();
});

describe("useComponentRegistry", () => {
  it("loads the root parent and every parent its containers declare", async () => {
    getChildComponents.mockImplementation(async (parent) => CATALOG[parent]);

    const { result } = renderHook(() => useComponentRegistry("Root"));

    await waitFor(() => expect(result.current.registry).not.toBeNull());
    expect(result.current.error).toBeNull();
    expect([...result.current.registry.byName.keys()].sort()).toEqual([
      "Container",
      "Leaf",
    ]);
    expect(Object.keys(result.current.registry.optionsByParent).sort()).toEqual(
      ["Leafable", "Root"],
    );
    expect(getChildComponents).toHaveBeenCalledTimes(2);
  });

  it("reports the failure and never exposes a partial registry", async () => {
    getChildComponents.mockImplementation(async (parent) => {
      if (parent === "Leafable") throw new Error("offline");
      return CATALOG[parent];
    });

    const { result } = renderHook(() => useComponentRegistry("Root"));

    await waitFor(() => expect(result.current.error).toBe("offline"));
    expect(result.current.registry).toBeNull();
  });

  it("prefers the detail the API sends with the failure", async () => {
    getChildComponents.mockRejectedValue({
      response: { data: { detail: "not allowed" } },
    });

    const { result } = renderHook(() => useComponentRegistry("Root"));

    await waitFor(() => expect(result.current.error).toBe("not allowed"));
  });

  it("fails when the answer is not a list", async () => {
    getChildComponents.mockResolvedValue({ components: [] });

    const { result } = renderHook(() => useComponentRegistry("Root"));

    await waitFor(() =>
      expect(result.current.error).toBe(
        "The components of Root did not arrive as a list.",
      ),
    );
    expect(result.current.registry).toBeNull();
  });
});
