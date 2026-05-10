import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import { Box, Paper } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
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
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

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
        accessorKey: "id",
        header: "ID",
        minSize: 30,
      },
      {
        accessorKey: "name",
        header: "Name",
        grow: 1,
        minSize: 200,
      },
      {
        accessorKey: "created",
        header: "Created",
        size: 200,
        accessorFn: (row) => formatDate(row.created),
      },
      {
        accessorKey: "last_modified",
        header: "Edited",
        size: 200,
        accessorFn: (row) => formatDate(row.last_modified),
      },
      {
        id: "actions",
        header: "Actions",
        grow: 1,
        minSize: 150,
        enableSorting: false,
        enableColumnFilter: false,
        Cell: ({ row }) => (
          <Box sx={{ display: "flex", gap: 1 }}>
            <EditExplorationAction
              onAction={() => handleSelectExploration(row.original)}
            />
            <RunExplorationAction
              onAction={() => handleRunExploration(row.original)}
            />
            <ViewExplorationResultsAction
              onAction={() => handleViewExplorationResults(row.original)}
            />
            <DeleteItemModal
              deleteFromTable={() => handleDeleteExploration(row.original.id)}
            />
          </Box>
        ),
      },
    ],
    [setUpdateTableFlag],
  );

  const table = useMaterialReactTable({
    columns,
    data: explorations,
    muiTableBodyCellProps: { sx: { whiteSpace: "pre" } },
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: {
      density: "compact",
      sorting: [{ id: "created", desc: true }],
    },
    state: { isLoading: loading },
    enableGlobalFilter: true,
  });

  return (
    <Box sx={{ height: "100%", width: "100%" }}>
      <Paper
        sx={{ px: 6, py: 4 }}
        // solves a mui problem related to putting datagrid inside another datagrid
        onClick={(event) => {
          event.target = document.body;
        }}
      >
        <MaterialReactTable table={table} />
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
