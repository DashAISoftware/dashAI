import React, {
  createContext,
  useContext,
  useRef,
  useCallback,
  useMemo,
} from "react";

const TourRegistryContext = createContext(null);
export const useTourRegistry = () => useContext(TourRegistryContext);

/**
 * App-level registry that tracks mounted TourProviders.
 * The last-registered entry is the "active" tour (stack semantics),
 * which lets multiple providers on one page coexist while the most
 * recently mounted one drives the navbar button.
 */
export function TourRegistryProvider({ children }) {
  const stackRef = useRef([]);
  const listenersRef = useRef(new Set());

  const notify = useCallback(() => {
    listenersRef.current.forEach((fn) => fn());
  }, []);

  const subscribe = useCallback((fn) => {
    listenersRef.current.add(fn);
    return () => listenersRef.current.delete(fn);
  }, []);

  const register = useCallback(
    (tourKey, handlers) => {
      const id = Symbol(tourKey);
      stackRef.current = [...stackRef.current, { id, tourKey, ...handlers }];
      notify();
      return id;
    },
    [notify],
  );

  const unregister = useCallback(
    (id) => {
      stackRef.current = stackRef.current.filter((e) => e.id !== id);
      notify();
    },
    [notify],
  );

  const update = useCallback(
    (id, handlers) => {
      stackRef.current = stackRef.current.map((e) =>
        e.id === id ? { ...e, ...handlers } : e,
      );
      notify();
    },
    [notify],
  );

  const getActive = useCallback(() => {
    const s = stackRef.current;
    return s.length > 0 ? s[s.length - 1] : null;
  }, []);

  const value = useMemo(
    () => ({ register, unregister, update, subscribe, getActive }),
    [register, unregister, update, subscribe, getActive],
  );

  return (
    <TourRegistryContext.Provider value={value}>
      {children}
    </TourRegistryContext.Provider>
  );
}
