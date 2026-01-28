import { createContext, useContext } from "react";

export const ThreePanelLayoutContext = createContext(null);

export function useThreePanelLayoutContext() {
  const ctx = useContext(ThreePanelLayoutContext);
  if (!ctx)
    throw new Error(
      "useThreePanelLayoutContext must be used within a ThreePanelLayoutProvider",
    );
  return ctx;
}
