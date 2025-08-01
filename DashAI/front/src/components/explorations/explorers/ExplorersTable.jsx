import React, { useCallback } from "react";
import PropTypes from "prop-types";

import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { Grid, Paper, Typography } from "@mui/material";

import DeleteItemModal from "../../custom/DeleteItemModal";
import { EditParametersDialog, EditColumnsDialog } from "..";
import { useExplorationsContext } from "../context";

/**
 * Table to display the explorers in the exploration
 * @param {Object} props
 * @param {Array} props.explorerTypes - List of available explorer types
 */
function ExplorersTable({ explorerTypes = [] }) {
  const { explorationData, setExplorationData, datasetColumns } =
    useExplorationsContext();
  const { explorers } = explorationData;

  const handleDeleteExplorer = useCallback(
    (id) => {
      setExplorationData((prev) => ({
        ...prev,
        explorers: prev.explorers.filter((explorer) => explorer.id !== id),
        deleted_explorers: [...prev.deleted_explorers, id],
      }));
    },
    [setExplorationData],
  );

  const handleUpdateColumns = useCallback(
    (id) => (newValues) => {
      let modifiedExplorer = explorers.find((explorer) => explorer.id === id);
      modifiedExplorer.columns = newValues;
      setExplorationData((prev) => ({
        ...prev,
        explorers: prev.explorers.map((explorer) =>
          explorer.id === id ? modifiedExplorer : explorer,
        ),
      }));
    },
    [explorers, setExplorationData],
  );

  const handleUpdateParameters = useCallback(
    (id) => (newValues) => {
      let modifiedExplorer = explorers.find((explorer) => explorer.id === id);
      modifiedExplorer.parameters = newValues;
      setExplorationData((prev) => ({
        ...prev,
        explorers: prev.explorers.map((explorer) =>
          explorer.id === id ? modifiedExplorer : explorer,
        ),
      }));
    },
    [explorers, setExplorationData],
  );

  const columns = React.useMemo(
    () => [
      {
        field: "name",
        headerName: "Name",
        minWidth: 200,
        flex: 1,
      },
      {
        field: "label",
        headerName: "Type",
        minWidth: 200,
        flex: 1,
        valueGetter: (params) => {
          const explorerType = explorerTypes.find(
            (explorer) => explorer.type === params.row.exploration_type,
          );
          return explorerType.label;
        },
      },
      {
        field: "exploration_type",
        headerName: "Component Name",
        minWidth: 200,
        flex: 1,
      },
      {
        field: "actions",
        headerName: "Actions",
        type: "actions",
        minWidth: 100,
        flex: 0.5,
        getActions: (params) => [
          <EditColumnsDialog
            key="edit-columns"
            datasetColumns={datasetColumns}
            updateValue={handleUpdateColumns(params.id)}
            initialValues={params.row.columns}
            explorerType={explorerTypes.find(
              (explorer) => explorer.type === params.row.exploration_type,
            )}
          />,

          <EditParametersDialog
            key="edit-component"
            componentToConfigure={params.row.exploration_type}
            updateParameters={handleUpdateParameters(params.id)}
            paramsInitialValues={params.row.parameters}
          />,
          <DeleteItemModal
            key="delete-component"
            deleteFromTable={() => handleDeleteExplorer(params.id)}
          />,
        ],
      },
    ],
    [
      explorerTypes,
      datasetColumns,
      handleDeleteExplorer,
      handleUpdateColumns,
      handleUpdateParameters,
    ],
  );

  return (
    <Paper sx={{ py: 1, px: 2 }}>
      {/* Title */}
      <Grid
        container
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="subtitle1" component="h3">
          Current explorers in the exploration
        </Typography>
      </Grid>

      {/* Models Table */}
      <DataGrid
        slots={{
          toolbar: GridToolbar,
        }}
        slotProps={{
          toolbar: {
            showQuickFilter: true,
          },
        }}
        rows={explorers}
        columns={columns}
        initialState={{
          pagination: {
            paginationModel: {
              pageSize: 5,
            },
          },
          columns: {
            columnVisibilityModel: {
              exploration_type: false,
            },
          },
        }}
        pageSizeOptions={[5, 10]}
        density="compact"
        autoHeight
        disableRowSelectionOnClick
      />
    </Paper>
  );
}

ExplorersTable.propTypes = {
  explorerTypes: PropTypes.array,
};

export default ExplorersTable;
