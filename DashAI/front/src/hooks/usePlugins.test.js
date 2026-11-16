import { act, renderHook } from "@testing-library/react";
import { checkPluginUpdates, getPluginUpdates } from "../api/plugins";
import { PLUGINS_CHANGED, usePluginUpdates } from "./usePlugins";

jest.mock("../api/plugins", () => ({
  checkPluginUpdates: jest.fn(),
  getInstalledPlugins: jest.fn(),
  getPluginUpdates: jest.fn(),
  getStore: jest.fn(async () => ({ plugins: [] })),
  pluginError: (error) => error,
}));

const STATUS = { checking: false, blocked_changes: 0, updates: {}, errors: {} };

test("a lookup reloads every view only if it blocked or unblocked a plugin", async () => {
  getPluginUpdates.mockResolvedValue(STATUS);
  checkPluginUpdates.mockResolvedValue(STATUS);
  const heard = jest.fn();
  window.addEventListener(PLUGINS_CHANGED, heard);
  const { result } = renderHook(() => usePluginUpdates());
  await act(async () => {}); // its first read, what it compares with

  await act(() => result.current.check());
  expect(heard).not.toHaveBeenCalled();
  // The POST answered the status, not read again.
  expect(getPluginUpdates).toHaveBeenCalledTimes(1); // when it mounted

  checkPluginUpdates.mockResolvedValue({ ...STATUS, blocked_changes: 1 });
  await act(() => result.current.check());
  expect(heard).toHaveBeenCalledTimes(1);
  await act(() => result.current.check()); // nothing new since
  expect(heard).toHaveBeenCalledTimes(1);
});

test("the lookup dashAI starts with is polled through a failed read", async () => {
  jest.useFakeTimers();
  getPluginUpdates
    .mockResolvedValueOnce({ ...STATUS, checking: true })
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValue({ ...STATUS, blocked_changes: 2 }); // the first test saw 1
  const heard = jest.fn();
  window.addEventListener(PLUGINS_CHANGED, heard);
  renderHook(() => usePluginUpdates()); // mounted again, read again

  for (let poll = 0; poll < 3; poll += 1) {
    await act(async () => jest.advanceTimersByTime(2500));
  }
  // Mounted, failed, ended, then again with every view.
  expect(getPluginUpdates).toHaveBeenCalledTimes(4);
  expect(heard).toHaveBeenCalledTimes(1); // it blocked or unblocked one
  jest.useRealTimers();
});
