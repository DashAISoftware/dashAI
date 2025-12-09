import React from "react";
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

function DatasetSelector({ datasets, selectedDataset, setSelectedDataset }) {
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
        <Alert severity="info" sx={{ mt: 2 }}>
          This dataset will be used to generate predictions for all{" "}
          {selectedDataset.total_rows} rows.
        </Alert>
      )}
    </Box>
  );
}

export default DatasetSelector;
