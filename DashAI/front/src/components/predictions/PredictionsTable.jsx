import React, { useState, useEffect } from "react";
import { Box, Typography, Paper, styled, Tooltip } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { formatDate, getColorByStatus } from "../../utils";
import { getPredictionStatus } from "../../utils/predictionStatus";

function PredictionsTable({ predictions, onItemClick }) {
  const StyledCell = styled("div")(({ theme, color }) => ({
    display: "inline-block",
    padding: theme.spacing(0.5),
    borderRadius: theme.shape.borderRadius,
    backgroundColor: color,
  }));

  const computeDuration = (start, end) => {
    if (!start || !end) return "-";

    const startTime = new Date(start);
    const endTime = end ? new Date(end) : new Date();
    const diffMs = endTime - startTime;

    if (diffMs < 0) return "-";

    const seconds = Math.floor(diffMs / 1000);
    return `${seconds}s`;
  };

  const columns = [
    {
      field: "type",
      headerName: "Type",
      flex: 1,
      minWidth: 150,
      renderCell: (params) => {
        const dataset = params?.row?.dataset;

        return dataset ? (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              height: "100%",
              overflow: "hidden",
              fontSize: "0.75rem",
            }}
          >
            <Typography
              variant="body2"
              fontWeight={500}
              sx={{ lineHeight: 1.1, fontSize: "inherit" }}
            >
              Dataset
            </Typography>

            <Tooltip placement="left" title={dataset.name}>
              <Typography
                variant="caption"
                color="text.secondary"
                noWrap
                sx={{
                  maxWidth: "100%",
                  fontSize: "inherit",
                }}
              >
                {dataset.name}
              </Typography>
            </Tooltip>
          </Box>
        ) : (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              height: "100%",
            }}
          >
            <Typography
              variant="body2"
              fontWeight={600}
              sx={{ lineHeight: 1.1, fontSize: "0.75rem" }}
            >
              Manual Input
            </Typography>
          </Box>
        );
      },
    },
    {
      field: "created",
      headerName: "Created",
      flex: 1.2,
      minWidth: 150,
      renderCell: (params) => formatDate(params?.row?.created),
    },
    {
      field: "duration",
      headerName: "Time",
      flex: 0.8,
      minWidth: 80,
      renderCell: (params) =>
        computeDuration(params?.row?.start_time, params?.row?.end_time),
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 100,
      renderCell: (params) => {
        const statusText = getPredictionStatus(params?.row?.status);
        return (
          <StyledCell color={getColorByStatus(statusText)}>
            {statusText}
          </StyledCell>
        );
      },
    },
  ];

  if (!predictions || predictions.length === 0) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <Typography color="text.secondary">No predictions yet</Typography>
        <Typography variant="caption" color="text.secondary">
          Run your first prediction to see it here
        </Typography>
      </Box>
    );
  }

  const rows = predictions.map((prediction) => ({
    id: prediction.id,
    ...prediction,
  }));

  return (
    <Paper sx={{ width: "100%" }}>
      <DataGrid
        rows={rows}
        columns={columns}
        disableRowSelectionOnClick
        onRowClick={(params) => onItemClick(params.row)}
        initialState={{
          pagination: {
            paginationModel: { pageSize: 10, page: 0 },
          },
        }}
        pageSizeOptions={[5, 10, 25, 50]}
        density="compact"
        sx={{
          fontSize: "0.75rem",
          "& .MuiDataGrid-cell": {
            fontSize: "0.75rem",
          },
          "& .MuiDataGrid-columnHeaders": {
            fontSize: "0.75rem",
          },
          "& .MuiDataGrid-row": {
            cursor: "pointer",
          },
          "& .MuiDataGrid-cell:focus": {
            outline: "none",
          },
          "& .MuiDataGrid-row:hover": {
            backgroundColor: "action.hover",
          },
        }}
      />
    </Paper>
  );
}

export default PredictionsTable;
