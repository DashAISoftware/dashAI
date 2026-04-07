import React, { useMemo } from "react";
import PropTypes from "prop-types";

import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

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
      col.renderCell({ value: row.original[col.field], row: { ...row, original: row.original } });
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
  const table = useMaterialReactTable({
    columns,
    data,
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: {
      density: "compact",
      pagination: { pageSize: 5, pageIndex: 0 },
    },
    state: { isLoading: loading },
    enableGlobalFilter: !minimalist,
    enableTopToolbar: !minimalist,
    enableColumnActions: minimalist ? false : undefined,
    enableSorting: !minimalist,
    enableColumnFilters: !minimalist,
  });

  return <MaterialReactTable table={table} />;
}

function TabularVisualizer({
  loading = false,
  rows = [],
  columns = [],
  minimalist = false,
}) {
  const theme = useTheme();
  const { i18n } = useTranslation();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const mrtColumns = useMemo(
    () => columns.map(toMrtColumn),
    [columns],
  );

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
