import React, { createContext, useContext, useState } from "react";

const ExplorersAndConvertersContext = createContext();

export const useExplorersAndConverters = () =>
  useContext(ExplorersAndConvertersContext);

export const ExplorersAndConvertersProvider = ({ children }) => {
  const [explorersAndConverters, setExplorersAndConverters] = useState([]);
  const [convertersLoaded, setConvertersLoaded] = useState(false);

  const value = {
    explorersAndConverters,
    setExplorersAndConverters,
    convertersLoaded,
    setConvertersLoaded,
  };

  return (
    <ExplorersAndConvertersContext.Provider value={value}>
      {children}
    </ExplorersAndConvertersContext.Provider>
  );
};
