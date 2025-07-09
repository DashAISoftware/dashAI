import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import { Box, Paper } from "@mui/material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";

import { formatDate } from "../../utils";
import DeleteItemModal from "../custom/DeleteItemModal";

import { useExplorationsContext } from "./context";
import {
  EditExplorationAction,
  RunExplorationAction,
  ViewExplorationResultsAction,
} from "./actions";

import {
  getExplorationsByDatasetId,
  deleteExploration,
} from "../../api/exploration";

/**
 * Component that renders a table with the explorations of a dataset.
 * It uses the module context to get the dataset id and fetch the explorations.
 * It also provides actions to edit, run, view results and delete an exploration.
 * @param {Object} props
 * @param {boolean} props.updateTableFlag - Flag to trigger an update of the table
 * @param {Function} props.setUpdateTableFlag - Function to set the updateTableFlag
 * @param {Function} props.onExplorationSelect - Function to handle the selection of an exploration
 * @param {Function} props.onExplorationRun - Function to handle the run of an exploration
 * @param {Function} props.onViewExplorationResults - Function to handle the view of the results of an exploration
 */
function ExplorationsTable({
  updateTableFlag = false,
  setUpdateTableFlag = (value) => {
    console.log("setUpdateTableFlag", value);
  },
  onExplorationSelect = (data) => {
    console.log("onExplorationSelect", data);
  },
  onExplorationRun = (data) => {
    console.log("onExplorationRun", data);
  },
  onViewExplorationResults = (data) => {
    console.log("onViewExplorationResults", data);
  },
}) {
  const { explorationData } = useExplorationsContext();
  const { dataset_id: datasetId } = explorationData;
  const { enqueueSnackbar } = useSnackbar();

  const [loading, setLoading] = useState(false);
  const [explorations, setExplorations] = useState([]);

  const getExplorations = () => {
    setLoading(true);
    getExplorationsByDatasetId(datasetId)
      .then((response) => {
        setExplorations(response);
      })
      .catch((error) => {
        console.log(error);
        enqueueSnackbar("Error while trying to fetch explorations", {
          variant: "error",
        });
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleSelectExploration = (data) => {
    onExplorationSelect(data);
  };

  const handleRunExploration = (data) => {
    onExplorationRun(data);
  };

  const handleViewExplorationResults = (data) => {
    onViewExplorationResults(data);
  };

  const handleDeleteExploration = (id) => {
    setLoading(true);
    deleteExploration(id)
      .then(() => {
        getExplorations();
        enqueueSnackbar("Exploration deleted successfully", {
          variant: "success",
        });
      })
      .catch((error) => {
        console.log(error);
        enqueueSnackbar("Error while trying to delete the exploration", {
          variant: "error",
        });
      })
      .finally(() => {
        setLoading(false);
      });
  };

  // Fetch explorations when the component is mounting
  useEffect(() => {
    getExplorations();
  }, []);

  // triggers an update of the table when updateFlag is set to true
  useEffect(() => {
    if (updateTableFlag) {
      setUpdateTableFlag(false);
      getExplorations();
    }
  }, [updateTableFlag]);

  // Columns definition
  const columns = useMemo(
    () => [
      {
        field: "id",
        headerName: "ID",
        minWidth: 30,
      },
      {
        field: "name",
        headerName: "Name",
        flex: 1,
        minwidth: 200,
      },
      {
        field: "created",
        headerName: "Created",
        width: 200,
        valueFormatter: (params) => formatDate(params.value),
      },
      {
        field: "last_modified",
        headerName: "Edited",
        width: 200,
        valueFormatter: (params) => formatDate(params.value),
      },
      {
        field: "actions",
        headerName: "Actions",
        flex: 1,
        minWidth: 150,
        type: "actions",
        getActions: (params) => [
          <EditExplorationAction
            key="edit-button"
            onAction={() => handleSelectExploration(params.row)}
          />,
          <RunExplorationAction
            key="run-button"
            onAction={() => handleRunExploration(params.row)}
          />,
          <ViewExplorationResultsAction
            key="view-results-button"
            onAction={() => handleViewExplorationResults(params.row)}
          />,
          <DeleteItemModal
            key="delete-button"
            deleteFromTable={() => handleDeleteExploration(params.row.id)}
          />,
        ],
      },
    ],
    [setUpdateTableFlag],
  );

  return (
    <Box sx={{ height: "100%", width: "100%" }}>
      <Paper
        sx={{ px: 3, py: 2 }}
        // solves a mui problem related to putting datagrid inside another datagrid
        onClick={(event) => {
          event.target = document.body;
        }}
      >
        <DataGrid
          loading={loading}
          autoHeight
          rows={explorations}
          columns={columns}
          disableRowSelectionOnClick
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 5,
              },
            },
            sorting: {
              sortModel: [{ field: "created", sort: "desc" }],
            },
          }}
          pageSizeOptions={[5, 10]}
          slots={{
            toolbar: GridToolbar,
          }}
          slotProps={{
            toolbar: {
              showQuickFilter: true,
            },
          }}
        />
      </Paper>
    </Box>
  );
}

ExplorationsTable.propTypes = {
  updateTableFlag: PropTypes.bool,
  setUpdateTableFlag: PropTypes.func,
  onExplorationSelect: PropTypes.func,
  onExplorationRun: PropTypes.func,
  onViewExplorationResults: PropTypes.func,
};

export default ExplorationsTable;
