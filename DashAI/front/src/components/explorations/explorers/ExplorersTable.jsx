import React, { useCallback } from "react";
import PropTypes from "prop-types";

import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { Box, Grid, Paper, Typography } from "@mui/material";

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
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

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
        accessorKey: "name",
        header: "Name",
        minSize: 200,
        grow: 1,
      },
      {
        id: "label",
        header: "Type",
        minSize: 200,
        grow: 1,
        accessorFn: (row) => {
          const explorerType = explorerTypes.find(
            (explorer) => explorer.type === row.exploration_type,
          );
          return explorerType ? explorerType.label : "";
        },
      },
      {
        accessorKey: "exploration_type",
        header: "Component Name",
        minSize: 200,
        grow: 1,
      },
      {
        id: "actions",
        header: "Actions",
        minSize: 100,
        grow: 0.5,
        enableSorting: false,
        enableColumnFilter: false,
        Cell: ({ row }) => (
          <Box sx={{ display: "flex", gap: 0.5 }}>
            <EditColumnsDialog
              datasetColumns={datasetColumns}
              updateValue={handleUpdateColumns(row.original.id)}
              initialValues={row.original.columns}
              explorerType={explorerTypes.find(
                (explorer) => explorer.type === row.original.exploration_type,
              )}
            />
            <EditParametersDialog
              componentToConfigure={row.original.exploration_type}
              updateParameters={handleUpdateParameters(row.original.id)}
              paramsInitialValues={row.original.parameters}
            />
            <DeleteItemModal
              deleteFromTable={() => handleDeleteExplorer(row.original.id)}
            />
          </Box>
        ),
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

  const table = useMaterialReactTable({
    columns,
    data: explorers,
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: {
      density: "compact",
      columnVisibility: { exploration_type: false },
    },
    enableGlobalFilter: true,
  });

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
      <MaterialReactTable table={table} />
    </Paper>
  );
}

ExplorersTable.propTypes = {
  explorerTypes: PropTypes.array,
};

export default ExplorersTable;
