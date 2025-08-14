import React, { createContext, useContext, useState } from "react";

const ExplorerAndConvertersContext = createContext();

export const useExplorerAndConverters = () =>
  useContext(ExplorerAndConvertersContext);

export const ExplorerAndConvertersProvider = ({ children }) => {
  const [explorersAndConverters, setExplorersAndConverters] = useState([]);

  const value = {
    explorersAndConverters,
    setExplorersAndConverters,
  };

  return (
    <ExplorerAndConvertersContext.Provider value={value}>
      {children}
    </ExplorerAndConvertersContext.Provider>
  );
};
