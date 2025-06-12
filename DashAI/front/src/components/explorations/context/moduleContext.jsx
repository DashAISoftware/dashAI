import React, { createContext, useState, useContext, useEffect } from "react";
import PropTypes from "prop-types";
import { getDatasetTypes } from "../../../api/datasets";
import { useSnackbar } from "notistack";

export const explorationModes = {
  EXPLORATION_CREATE: {
    name: "create",
    modalTitle: "",
    title: "New Exploration",
    body: "",
    backButton: true,
    creatorButton: false,
    reloaderButton: false,
    showModalTitle: false,
  },
  EXPLORATION_EDIT: {
    name: "edit",
    modalTitle: "",
    title: "Edit Exploration",
    body: "",
    backButton: true,
    creatorButton: false,
    reloaderButton: false,
    showModalTitle: false,
  },
  EXPLORATION_VISUALIZE: {
    name: "visualize",
    modalTitle: "",
    title: "Visualize Results",
    body: "",
    backButton: true,
    creatorButton: false,
    reloaderButton: true,
    showModalTitle: false,
  },
  EXPLORATION_LIST: {
    name: "history",
    modalTitle: "Exploration Module",
    title: "Recent Explorations",
    body: "",
    backButton: false,
    creatorButton: true,
    reloaderButton: true,
    showModalTitle: true,
  },
  EXPLORATION_RUN: {
    name: "run",
    modalTitle: "",
    title: "Run Exploration",
    body: "",
    backButton: true,
    creatorButton: false,
    reloaderButton: true,
    showModalTitle: false,
  },
};

const defaultExplorationMode = explorationModes.EXPLORATION_LIST;

const defaultExplorationData = {
  id: null,
  dataset_id: null,
  created: null,
  last_modified: null,
  name: "",
  description: "",
  explorers: [],
  deleted_explorers: [],
};

const defaultExplorerData = {
  id: null,
  exploration_id: null,
  created: null,
  last_modified: null,
  columns: [],
  exploration_type: "",
  parameters: {},
  exploration_path: "",
  name: "",
  delivery_time: null,
  start_time: null,
  end_time: null,
  status: null,
};

export const contextDefaults = {
  defaultExplorationMode,
  defaultExplorationData,
  defaultExplorerData,
};

// Create the context
const ExplorationsContext = createContext({
  explorationMode: defaultExplorationMode,
  setExplorationMode: (prev) => {},
  explorationData: defaultExplorationData,
  setExplorationData: (prev) => {},
  explorerData: defaultExplorerData,
  setExplorerData: (prev) => {},
  datasetColumns: [],
  setDatasetColumns: (prev) => {},
  refreshFlag: false,
  setRefreshFlag: (prev) => {},
});

// Create a provider component
export function ExplorationsProvider({
  children,
  datasetId,
  explorationId = null,
  explorerId = null,
}) {
  const { enqueueSnackbar } = useSnackbar();
  // Instance variables for the exploration module
  const [explorationMode, setExplorationMode] = useState(
    defaultExplorationMode,
  );

  const [explorationData, setExplorationData] = useState({
    ...defaultExplorationData,
    id: explorationId,
    dataset_id: datasetId,
  });

  const [explorerData, setExplorerData] = useState({
    ...defaultExplorerData,
    id: explorerId,
    exploration_id: explorationId,
  });

  const [refreshFlag, setRefreshFlag] = useState(false);
  const [datasetColumns, setDatasetColumns] = useState([]);
  const fetchDatasetColumns = () => {
    if (datasetId) {
      getDatasetTypes(datasetId)
        .then((data) => {
          setDatasetColumns(
            Object.keys(data).map((name, idx) => {
              return {
                id: idx,
                columnName: name,
                valueType: data[name].type,
                dataType: data[name].dtype,
              };
            }),
          );
        })
        .catch((error) => {
          console.error(error);
          enqueueSnackbar("Failed to load dataset types.", {
            variant: "error",
          });
        });
    }
  };

  // Fetch dataset columns type specification when datasetId changes and on mount
  useEffect(() => {
    fetchDatasetColumns();
  }, [datasetId]);

  // Fetch dataset columns type specification when refreshFlag is set
  useEffect(() => {
    if (refreshFlag) {
      fetchDatasetColumns();
      setRefreshFlag(false);
    }
  }, [refreshFlag]);

  return (
    <ExplorationsContext.Provider
      value={{
        explorationMode,
        setExplorationMode,
        explorationData,
        setExplorationData,
        explorerData,
        setExplorerData,
        datasetColumns,
        setDatasetColumns,
        refreshFlag,
        setRefreshFlag,
      }}
    >
      {children}
    </ExplorationsContext.Provider>
  );
}

ExplorationsProvider.propTypes = {
  children: PropTypes.node.isRequired,
  datasetId: PropTypes.number.isRequired,
  explorationId: PropTypes.number,
  explorerId: PropTypes.number,
};

// Create a hook to use the context
export const useExplorationsContext = () => {
  const context = useContext(ExplorationsContext);
  if (!context.explorationData.dataset_id) {
    throw new Error(
      "useExplorationContext must be used within a ExplorationProvider which has a datasetId",
    );
  }
  return context;
};
