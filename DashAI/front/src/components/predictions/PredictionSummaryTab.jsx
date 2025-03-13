import React, { useEffect, useState } from "react";
import { Paper, Grid, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";

function PredictionSummaryTab({ summary }) {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const handleCloseContent = () => {
    setOpen(false);
  };

  const rows =
    summary["class_distribution"]?.map((row, index) => ({
      id: index + 1,
      ...row,
    })) || [];

  const columns = React.useMemo(() => [
    {
      field: "id",
      headerName: "ID",
      minWidth: 30,
      editable: false,
    },
    {
      field: "Class",
      HeaderName: "Class",
      minWidth: 200,
      editable: false,
    },
    {
      field: "Ocurrences",
      HeaderName: "Ocurrences",
      minWidth: 200,
      editable: false,
    },
    {
      field: "Percentage",
      HeaderName: "Percentage",
      minWidth: 200,
      editable: false,
    },
  ]);
  return (
    <Grid
      container
      direction="row"
      justifyContent="space-around"
      alignItems="flex-start"
      spacing={2}
    >
      {/* Total Data Points */}
      <Grid item xs={5} sx={{ mb: 2 }}>
        <Typography variant="subtitle1">Total data points</Typography>
        <Typography variant="body2" style={{ color: "darkgray" }}>
          {summary["total_data_points"]}
        </Typography>
      </Grid>

      {/* Unique Classes Predicted */}
      <Grid item xs={6}>
        <Typography variant="subtitle1">Unique classes predicted</Typography>
        <Typography variant="body2" style={{ color: "darkgray" }}>
          {summary["Unique_classes"]}
        </Typography>
      </Grid>
      <Grid item xs={12}>
        <Paper sx={{ width: "100%" }}>
          <Typography variant="h6" component="h2" sx={{ p: 2 }}>
            Class distribution
          </Typography>
          {summary["class_distribution"] ? (
            <DataGrid
              rows={rows}
              columns={columns}
              columnVisibilityModel={{ id: false }}
              justifyContent="center"
              disableRowSelectionOnClick
            />
          ) : (
            <Typography
              variant="subtitle1"
              component="h3"
              sx={{ p: 1 }}
              color="text.secondary"
            >
              No data available
            </Typography>
          )}
        </Paper>
      </Grid>
    </Grid>
  );
}

export default PredictionSummaryTab;
