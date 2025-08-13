import React from "react";
import PropTypes from "prop-types";

import { DataGrid, GridToolbar } from "@mui/x-data-grid";

function TabularVisualizer({
  loading = false,
  rows = [],
  columns = [],
  ...props
}) {
  return (
    <DataGrid
      loading={loading}
      rows={rows}
      columns={columns}
      autoHeight
      disableRowSelectionOnClick
      slots={{
        toolbar: GridToolbar,
      }}
      slotProps={{
        toolbar: {
          showQuickFilter: true,
        },
      }}
      initialState={{
        pagination: {
          paginationModel: {
            pageSize: 5,
          },
        },
      }}
      pageSizeOptions={[5, 10, 20]}
      density="compact"
      {...props}
    />
  );
}

TabularVisualizer.propTypes = {
  loading: PropTypes.bool,
  rows: PropTypes.array,
  columns: PropTypes.array,
};

export default TabularVisualizer;
