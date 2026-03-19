import React from "react";
import PropTypes from "prop-types";

import { DataGrid, GridToolbar } from "@mui/x-data-grid";

const EMPTY_ARRAY = [];

function TabularVisualizer({
  loading = false,
  rows = EMPTY_ARRAY,
  columns = EMPTY_ARRAY,
  minimalist = false,
  ...props
}) {
  const minimalistProps = minimalist
    ? {
        disableColumnMenu: true,
        disableColumnFilter: true,
        disableColumnSelector: true,
        disableDensitySelector: true,
        density: "compact",
        slots: {},
        slotProps: {},
        sx: {
          // height: "100%",
          width: "100%",
        },
        initialState: {
          pagination: {
            paginationModel: {
              pageSize: 5,
            },
          },
        },
        noRowsOverlay: {
          style: { height: "100%" },
        },
        pageSizeOptions: [5],
      }
    : {
        autoHeight: true,
        disableRowSelectionOnClick: true,
        slots: {
          toolbar: GridToolbar,
        },
        slotProps: {
          toolbar: {
            showQuickFilter: true,
          },
        },
        initialState: {
          pagination: {
            paginationModel: {
              pageSize: 5,
            },
          },
        },
        pageSizeOptions: [5, 10, 20],
        density: "compact",
      };

  return (
    <DataGrid
      loading={loading}
      rows={rows}
      columns={columns}
      {...minimalistProps}
      {...props}
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
