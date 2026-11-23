import { renderHook, waitFor } from "@testing-library/react";
import useQueryTransformationOptions from "./useQueryTransformationOptions";
import {
  getGeneratorComponents,
  getQueryTransformationComponents,
  getQueryTransformationPrompts,
} from "../api/rag";

jest.mock("../api/rag", () => ({
  getGeneratorComponents: jest.fn(),
  getQueryTransformationComponents: jest.fn(),
  getQueryTransformationPrompts: jest.fn(),
}));

beforeEach(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  getQueryTransformationComponents.mockResolvedValue([{ name: "Expander" }]);
  getQueryTransformationPrompts.mockResolvedValue([{ name: "Prompt" }]);
  getGeneratorComponents.mockResolvedValue([{ name: "Generator" }]);
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe("useQueryTransformationOptions", () => {
  it("loads the three option lists", async () => {
    const { result } = renderHook(() => useQueryTransformationOptions());

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.transformers).toEqual([{ name: "Expander" }]);
    expect(result.current.prompts).toEqual([{ name: "Prompt" }]);
    expect(result.current.generators).toEqual([{ name: "Generator" }]);
    expect(result.current.loadError).toBeNull();
  });

  it("keeps the first failure when several requests fail", async () => {
    getQueryTransformationComponents.mockRejectedValue(new Error("first"));
    getGeneratorComponents.mockRejectedValue(new Error("second"));

    const { result } = renderHook(() => useQueryTransformationOptions());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.loadError).toBe("first");
    expect(result.current.transformers).toEqual([]);
    expect(result.current.generators).toEqual([]);
    expect(result.current.prompts).toEqual([{ name: "Prompt" }]);
  });

  it("prefers the detail the API sends with a failure", async () => {
    getQueryTransformationPrompts.mockRejectedValue({
      response: { data: { detail: "forbidden" } },
    });

    const { result } = renderHook(() => useQueryTransformationOptions());

    await waitFor(() => expect(result.current.loadError).toBe("forbidden"));
  });

  it.each([
    ["transformers", getQueryTransformationComponents, "query transformers"],
    ["prompts", getQueryTransformationPrompts, "query transformation prompts"],
    ["generators", getGeneratorComponents, "generation models"],
  ])("fails when the %s answer is not a list", async (key, request, what) => {
    request.mockResolvedValue({ items: [] });

    const { result } = renderHook(() => useQueryTransformationOptions());

    await waitFor(() =>
      expect(result.current.loadError).toBe(
        `The ${what} did not arrive as a list.`,
      ),
    );
    expect(result.current[key]).toEqual([]);
  });
});
