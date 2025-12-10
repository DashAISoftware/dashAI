import React, { useCallback } from "react";
import {
  Box,
  Typography,
  FormControl,
  Select,
  MenuItem,
  Paper,
  InputLabel,
  Alert,
} from "@mui/material";
import DatasetTable from "../../notebooks/dataset/DatasetTable";
import { getDatasetFile } from "../../../api/datasets";

function DatasetSelector({ datasets, selectedDataset, setSelectedDataset }) {
  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(
        selectedDataset.file_path,
        page,
        pageSize,
      );
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [selectedDataset],
  );

  return (
    <Box sx={{ mb: 3 }}>
      <FormControl fullWidth>
        <InputLabel>Select Dataset</InputLabel>
        <Select
          value={selectedDataset?.id || ""}
          label="Select Dataset"
          onChange={(e) => {
            const dataset = datasets.find((d) => d.id === e.target.value);
            setSelectedDataset(dataset);
          }}
        >
          {datasets.map((dataset) => (
            <MenuItem key={dataset.id} value={dataset.id}>
              {dataset.name} ({dataset.total_rows} rows)
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {selectedDataset && (
        <>
          <Alert severity="info" sx={{ mt: 2 }}>
            This dataset will be used to generate predictions for all{" "}
            {selectedDataset.total_rows} rows.
          </Alert>
          <Paper>
            <DatasetTable
              fetchPage={fetchDatasetPage}
              initialPageSize={10}
              autoHeight={true}
              datasetPath={selectedDataset.file_path}
              sx={{ mt: 2 }}
              slots={{ toolbar: null }}
            />
          </Paper>
        </>
      )}
    </Box>
  );
}

export default DatasetSelector;
