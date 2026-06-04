import React, { useMemo } from "react";
import PropTypes from "prop-types";

import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { Box } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTableLocalization } from "../../../../utils/useTableLocalization";

/**
 * Convert a DataGrid-style column definition to an MRT column definition.
 * Handles: field→accessorKey, headerName→header, flex→grow,
 *          width/minWidth→size/minSize, renderCell→Cell,
 *          sortable→enableSorting, disableColumnMenu→enableColumnActions.
 */
function toMrtColumn(col) {
  const mrt = {};

  if (col.field !== undefined) mrt.accessorKey = col.field;
  if (col.headerName !== undefined) mrt.header = col.headerName;
  if (col.flex !== undefined) mrt.grow = col.flex;
  if (col.width !== undefined) mrt.size = col.width;
  if (col.minWidth !== undefined) mrt.minSize = col.minWidth;
  if (col.sortable === false) mrt.enableSorting = false;
  if (col.disableColumnMenu === true) mrt.enableColumnActions = false;
  if (col.filterable === false) mrt.enableColumnFilter = false;

  if (col.renderCell) {
    mrt.Cell = ({ row }) =>
      col.renderCell({
        value: row.original[col.field],
        row: { ...row, original: row.original },
      });
  }

  if (col.valueGetter) {
    mrt.accessorFn = (row) => col.valueGetter({ row });
  }

  return mrt;
}

function TabularVisualizerInner({
  loading,
  columns,
  data,
  localization,
  theme,
  minimalist,
}) {
  const fullSizeTableStyles = minimalist
    ? {
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }
    : undefined;
  const tablePaperStyles = {
    border: 1,
    borderColor: theme.palette.divider,
    borderRadius: minimalist ? 0 : 1,
    ...(fullSizeTableStyles ?? {}),
  };

  const table = useMaterialReactTable({
    columns,
    data,
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: {
      elevation: 0,
      sx: tablePaperStyles,
    },
    muiTableContainerProps: minimalist
      ? {
          sx: {
            flex: 1,
            width: "100%",
            height: "100%",
          },
        }
      : undefined,
    localization,
    initialState: {
      density: "compact",
      pagination: { pageSize: minimalist ? 5 : 10, pageIndex: 0 },
    },
    muiPaginationProps: minimalist ? { showRowsPerPage: false } : undefined,
    state: { isLoading: loading },
    enableGlobalFilter: !minimalist,
    enableTopToolbar: !minimalist,
    enableColumnActions: minimalist ? false : undefined,
    enableSorting: !minimalist,
    enableColumnFilters: !minimalist,
  });

  return minimalist ? (
    <Box sx={{ width: "100%", height: "100%", display: "flex" }}>
      <MaterialReactTable table={table} />
    </Box>
  ) : (
    <MaterialReactTable table={table} />
  );
}

function TabularVisualizer({
  loading = false,
  rows = [],
  columns = [],
  minimalist = false,
}) {
  const theme = useTheme();
  const localization = useTableLocalization();

  const mrtColumns = useMemo(() => columns.map(toMrtColumn), [columns]);

  return (
    <TabularVisualizerInner
      loading={loading}
      columns={mrtColumns}
      data={rows}
      localization={localization}
      theme={theme}
      minimalist={minimalist}
    />
  );
}

TabularVisualizer.propTypes = {
  loading: PropTypes.bool,
  rows: PropTypes.array,
  columns: PropTypes.array,
  minimalist: PropTypes.bool,
};

export default TabularVisualizer;
