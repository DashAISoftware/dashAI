import React, { useState } from "react";
import { Grid, Paper } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";

function PredictionSampleTab({ summary, type }) {
  const columns = React.useMemo(() => {
    const rows = summary["sample_data"] || [];

    // Dynamically generate columns from input fields
    const inputColumns = [];
    if (rows.length > 0 && rows[0].input) {
      Object.keys(rows[0].input).forEach((key) => {
        inputColumns.push({
          field: key,
          headerName: key,
          minWidth: 150,
          editable: false,
          valueGetter: (value, row) => row.input?.[key],
        });
      });
    }

    const typeSpecificColumn = {
      field: "value",
      headerName: "Value",
      minWidth: 100,
      editable: false,
    };

    return [...inputColumns, typeSpecificColumn];
  }, [type, summary]);

  // Create column grouping model
  const columnGroupingModel = React.useMemo(() => {
    const rows = summary["sample_data"] || [];
    const inputColumnFields = [];

    if (rows.length > 0 && rows[0].input) {
      Object.keys(rows[0].input).forEach((key) => {
        inputColumnFields.push(key);
      });
    }

    return [
      {
        groupId: "inputColumns",
        headerName: "Input Columns",
        children: inputColumnFields.map((field) => ({ field })),
      },
    ];
  }, [summary]);

  const rows = summary["sample_data"] || [];

  return (
    <Grid
      container
      direction="row"
      justifyContent="space-around"
      alignItems="flex-start"
      spacing={2}
    >
      <Grid size={{ xs: 12 }}>
        <Paper sx={{ mt: 2, height: 400 }}>
          <DataGrid
            rows={rows}
            columns={columns}
            disableRowSelectionOnClick
            columnGroupingModel={columnGroupingModel}
          />
        </Paper>
      </Grid>
    </Grid>
  );
}

export default PredictionSampleTab;
