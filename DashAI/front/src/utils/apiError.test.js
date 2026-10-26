import { getApiDetail, getApiErrorMessage } from "./apiError";

const answered = (detail) => ({
  message: "Request failed with status code 404",
  response: { data: { detail } },
});

describe("getApiDetail", () => {
  it.each([
    [
      "a string",
      "Task X not found in the registry.",
      "Task X not found in the registry.",
    ],
    ["a nested detail", { detail: "Duplicate" }, "Duplicate"],
    ["a validation list", [{ msg: "a" }, { msg: "b" }], "a; b"],
  ])("reads %s", (_name, detail, expected) => {
    expect(getApiDetail(answered(detail), "fallback")).toBe(expected);
  });

  it("gives the fallback when the backend said nothing", () => {
    expect(getApiDetail({ message: "Network Error" }, "fallback")).toBe(
      "fallback",
    );
  });
});

describe("getApiErrorMessage", () => {
  it("reads the backend's detail first", () => {
    expect(getApiErrorMessage(answered("Duplicate"), "fallback")).toBe(
      "Duplicate",
    );
  });

  it("then axios's own message, then the fallback", () => {
    expect(getApiErrorMessage({ message: "Network Error" }, "fallback")).toBe(
      "Network Error",
    );
    expect(getApiErrorMessage({}, "fallback")).toBe("fallback");
  });
});
