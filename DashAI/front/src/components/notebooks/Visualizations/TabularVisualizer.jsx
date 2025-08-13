import React from "react";
import PropTypes from "prop-types";

import { DataGrid, GridToolbar } from "@mui/x-data-grid";

function TabularVisualizer({
  loading = false,
  rows = [],
  columns = [],
  minimalist = false,
  ...props
}) {
  const minimalistProps = minimalist
    ? {
        hideFooter: true,
        disableColumnMenu: true,
        disableColumnFilter: true,
        disableColumnSelector: true,
        disableDensitySelector: true,
        density: "compact",
        slots: {},
        slotProps: {},
        sx: {
          height: "100%",
          width: "100%",
        },
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
