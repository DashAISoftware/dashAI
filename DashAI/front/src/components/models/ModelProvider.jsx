import React, { createContext, useContext, useState, useCallback } from "react";

const ModelContext = createContext(null);

export function ModelProvider({ children }) {
  const [selectedModel, setSelectedModel] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);

  const selectModel = useCallback((model) => {
    setSelectedModel(model);
    setConfigOpen(true);
  }, []);

  const closeConfig = useCallback(() => {
    setConfigOpen(false);
    setSelectedModel(null);
  }, []);

  return (
    <ModelContext.Provider
      value={{
        selectedModel,
        configOpen,
        selectModel,
        closeConfig,
        setSelectedModel,
        setConfigOpen,
      }}
    >
      {children}
    </ModelContext.Provider>
  );
}

export function useModelContext() {
  return useContext(ModelContext);
}
