import React, { createContext, useContext, useState } from "react";

const ExplorersAndConvertersContext = createContext();

export const useExplorersAndConverters = () =>
  useContext(ExplorersAndConvertersContext);

export const ExplorersAndConvertersProvider = ({ children }) => {
  const [explorersAndConverters, setExplorersAndConverters] = useState([]);

  const value = {
    explorersAndConverters,
    setExplorersAndConverters,
  };

  return (
    <ExplorersAndConvertersContext.Provider value={value}>
      {children}
    </ExplorersAndConvertersContext.Provider>
  );
};
