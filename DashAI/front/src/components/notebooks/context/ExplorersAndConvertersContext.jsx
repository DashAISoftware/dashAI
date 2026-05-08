import React, { createContext, useContext, useState, useCallback } from "react";

const ExplorersAndConvertersContext = createContext();

export const useExplorersAndConverters = () =>
  useContext(ExplorersAndConvertersContext);

export const ExplorersAndConvertersProvider = ({ children }) => {
  const [explorersAndConverters, setExplorersAndConverters] = useState([]);
  const [lastAddedItemId, setLastAddedItemId] = useState(null);
  const clearLastAddedItemId = useCallback(() => setLastAddedItemId(null), []);

  const value = {
    explorersAndConverters,
    setExplorersAndConverters,
    lastAddedItemId,
    setLastAddedItemId,
    clearLastAddedItemId,
  };

  return (
    <ExplorersAndConvertersContext.Provider value={value}>
      {children}
    </ExplorersAndConvertersContext.Provider>
  );
};
