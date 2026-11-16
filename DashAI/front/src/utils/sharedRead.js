import { useEffect, useSyncExternalStore } from "react";

/**
 * One copy of what `read` returns, for the whole app: every view that uses it
 * shows the same data and opens with the last value read.
 *
 * Read when the first view mounts, again whenever the `refreshOn` window
 * event is sent and, with `revalidate`, each time a view mounts (unless a read
 * is on its way). Only the newest read lands; a failed one keeps the last data
 * and sets `error` (the thrown value).
 *
 * The `refreshOn` listener is added here, when the module creating the store
 * loads: a store built on another one (`read` calls its `fresh()`) is created
 * after it, so on that event its read joins the one the other just started.
 *
 * @param {object} options
 * @param {() => Promise<any>} options.read - The request.
 * @param {any} options.empty - The data before the first read.
 * @param {string} [options.refreshOn] - Window event that makes it stale.
 * @param {boolean} [options.revalidate] - Read again when a view mounts.
 */
export function sharedRead({ read, empty, refreshOn, revalidate = false }) {
  let state = { data: empty, error: null };
  let version = 0;
  let reading = null; // the newest read's request, while on its way
  const listeners = new Set();

  const get = () => state;
  const set = (change) => {
    state = { ...state, ...change };
    listeners.forEach((listener) => listener());
  };

  // Reads now (with `readNow` instead of `read`, e.g. a POST that answers
  // the same data); resolves with the error it failed with, or null.
  const refresh = async (readNow = read) => {
    const current = ++version;
    const request = readNow();
    reading = request;
    try {
      const data = await request;
      if (current === version) set({ data, error: null });
      return null;
    } catch (error) {
      if (current === version) set({ error });
      return error;
    } finally {
      if (reading === request) reading = null;
    }
  };

  // The data as the API has it now: the read on its way (the newest, even one
  // started meanwhile) or a new one. Rejects if that read fails.
  const fresh = async () => {
    if (!reading) refresh();
    let data;
    while (reading) {
      try {
        data = await reading;
      } catch (error) {
        if (!reading) throw error; // else an older read failed: wait the newer
      }
    }
    return data;
  };

  const mounted = () => {
    if (!reading && (revalidate || version === 0)) refresh();
  };

  const subscribe = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  if (refreshOn) window.addEventListener(refreshOn, () => refresh());

  return { get, set, refresh, fresh, mounted, subscribe };
}

export function useSharedRead(store) {
  useEffect(store.mounted, [store]);
  return useSyncExternalStore(store.subscribe, store.get);
}
