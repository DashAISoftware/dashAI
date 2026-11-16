import { useEffect, useState } from "react";

const remembered = new Map();

/**
 * `useState` that outlives its component while the app is open: a view that
 * unmounts (e.g. opening a detail and going back) opens again with what was
 * chosen last. `key` names the value across the app.
 *
 * @param {string} key - Unique name, e.g. "plugins.filters".
 * @param {any} initial - The value the first time.
 */
export function useRememberedState(key, initial) {
  const [value, setValue] = useState(() =>
    remembered.has(key) ? remembered.get(key) : initial,
  );
  useEffect(() => {
    remembered.set(key, value);
  }, [key, value]);
  return [value, setValue];
}
