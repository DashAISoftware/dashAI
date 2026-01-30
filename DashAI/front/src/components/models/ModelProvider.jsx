import React, { createContext, useContext, useState, useCallback } from "react";

const ModelContext = createContext(null);

export function ModelProvider({ children }) {
  const [selectedModel, setSelectedModel] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);

  // Selecciona un modelo y abre el modal de configuración
  const selectModel = useCallback((model) => {
    setSelectedModel(model);
    setConfigOpen(true);
  }, []);

  // Cierra el modal de configuración
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
