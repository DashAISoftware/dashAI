import { renderHook, waitFor } from "@testing-library/react";
import { getComponents } from "../api/component";
import {
  TaskMetadataError,
  fetchTaskMetadata,
  useTaskMetadata,
} from "./useTaskMetadata";

jest.mock("../api/component", () => ({ getComponents: jest.fn() }));

// The module keeps one request per task name for the whole run, so every
// test uses task names of its own.
const answers = (byTask) => {
  getComponents.mockImplementation(({ model }) => byTask[model]());
};
const never = () => new Promise(() => {});

describe("useTaskMetadata", () => {
  it("forgets the previous task's metadata as soon as the task changes", async () => {
    answers({
      TaskA: () => Promise.resolve({ metadata: { io_roles: "A" } }),
      TaskB: never,
    });
    const { result, rerender } = renderHook(
      ({ name }) => useTaskMetadata(name),
      { initialProps: { name: "TaskA" } },
    );
    await waitFor(() => expect(result.current).toEqual({ io_roles: "A" }));

    rerender({ name: "TaskB" });

    expect(result.current).toBeNull();
  });

  it("gives empty metadata for a task that cannot be read", async () => {
    answers({ TaskC: () => Promise.reject(new Error("404")) });

    const { result } = renderHook(() => useTaskMetadata("TaskC"));

    await waitFor(() => expect(result.current).toEqual({}));
  });
});

describe("fetchTaskMetadata", () => {
  it("rejects naming the task and the backend's reason, and asks again next time", async () => {
    answers({
      TaskD: () =>
        Promise.reject({
          response: {
            status: 404,
            data: { detail: "Component TaskD not found in the registry." },
          },
        }),
    });

    const failure = fetchTaskMetadata("TaskD");

    await expect(failure).rejects.toBeInstanceOf(TaskMetadataError);
    await expect(failure).rejects.toMatchObject({
      taskName: "TaskD",
      detail: "Component TaskD not found in the registry.",
    });
    answers({ TaskD: () => Promise.resolve({ metadata: { io_roles: "D" } }) });
    await expect(fetchTaskMetadata("TaskD")).resolves.toEqual({
      io_roles: "D",
    });
  });
});
