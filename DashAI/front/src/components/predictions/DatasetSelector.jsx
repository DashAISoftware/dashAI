import React, { useState, useEffect } from "react";
import { Alert, AlertTitle, Link, Paper, Typography } from "@mui/material";

import { DataGrid } from "@mui/x-data-grid";

import { Link as RouterLink } from "react-router-dom";

export default function DatasetSelector({
  datasets,
  columns,
  loading,
  requestError,
  setDatasetsSelected,
  datasetsSelected,
}) {
  return (
    <>
      {datasets.length === 0 && !loading && !requestError && (
        <React.Fragment>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <AlertTitle>There is no datasets available.</AlertTitle>
            Go to{" "}
            <Link component={RouterLink} to="/app/data">
              data tab
            </Link>{" "}
            to upload one first.
          </Alert>
          <Typography></Typography>
        </React.Fragment>
      )}
      <Paper>
        <DataGrid
          rows={datasets}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 10,
              },
            },
          }}
          onRowSelectionModelChange={(newRowSelectionModel) => {
            setDatasetsSelected(newRowSelectionModel);
          }}
          rowSelectionModel={datasetsSelected}
          density="compact"
          pageSizeOptions={[10]}
          loading={loading}
          autoHeight
          hideFooterSelectedRowCount
        />
      </Paper>
    </>
  );
}
