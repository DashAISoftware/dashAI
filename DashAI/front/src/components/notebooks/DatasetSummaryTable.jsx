// DatasetSummaryTable.js
import React, { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import { DataGrid } from "@mui/x-data-grid";
import {
  getDatasetSampleByFilePath as getDatasetSampleRequest,
  getDatasetTypesByFilePath as getDatasetTypesRequest,
} from "../../api/datasets";
import { Box, Typography, CircularProgress, Paper } from "@mui/material";

function DatasetSummaryTable({ file }) {
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState([]);
  const [columns, setColumns] = useState([]);

  const getDatasetInfo = async () => {
    setLoading(true);
    try {
      const dataset = await getDatasetSampleRequest(file);
      const types = await getDatasetTypesRequest(file);

      // Create DataGrid columns
      const gridColumns = [
        { field: "rowLabel", headerName: "", width: 150, sortable: false },
      ];
      Object.keys(dataset).forEach((col) => {
        gridColumns.push({
          field: col,
          headerName: col,
          flex: 1,
          minWidth: 150,
          sortable: false,
        });
      });

      // Build rows: 1 row for column type, 1 for data type, 1 for sample
      const typeRow = { id: 0, rowLabel: "Column Type" };
      const dtypeRow = { id: 1, rowLabel: "Data Type" };
      const sampleRow = { id: 2, rowLabel: "Example" };

      Object.keys(dataset).forEach((col) => {
        typeRow[col] = types[col]?.type ?? "";
        dtypeRow[col] = types[col]?.dtype ?? "";
        sampleRow[col] = dataset[col]?.[0] ?? "";
      });

      setColumns(gridColumns);
      setRows([typeRow, dtypeRow, sampleRow]);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset.", {
        variant: "error",
      });
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getDatasetInfo();
  }, []);

  return (
    <Paper elevation={2} sx={{ p: 2, borderRadius: 2 }}>
      <Typography variant="h6" gutterBottom>
        Dataset Summary
      </Typography>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
          <CircularProgress />
        </Box>
      ) : (
        <DataGrid
          rows={rows}
          columns={columns}
          hideFooter
          autoHeight
          disableColumnMenu
          disableRowSelectionOnClick
          sx={{
            "& .MuiDataGrid-columnHeaders": {
              fontWeight: "bold",
            },
            "& .MuiDataGrid-cell": {
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            },
          }}
        />
      )}
    </Paper>
  );
}

export default DatasetSummaryTable;
