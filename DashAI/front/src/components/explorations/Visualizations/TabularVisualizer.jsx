import React from "react";
import PropTypes from "prop-types";

import { DataGrid, GridToolbar } from "@mui/x-data-grid";

const EMPTY_ARRAY = [];

function TabularVisualizer({
  loading = false,
  rows = EMPTY_ARRAY,
  columns = EMPTY_ARRAY,
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
