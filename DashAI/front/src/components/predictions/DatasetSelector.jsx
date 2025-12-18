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
  Chip,
} from "@mui/material";
import DatasetTable from "../notebooks/dataset/DatasetTable";
import { getDatasetFile } from "../../api/datasets";

function DatasetSelector({
  experiment,
  datasets,
  selectedDataset,
  setSelectedDataset,
}) {
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
            <Box sx={{ fontWeight: 600, mb: 1, fontSize: "1rem" }}>
              Prediction Configuration
            </Box>

            <Box sx={{ mb: 1 }}>
              <strong>Input columns:</strong>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 0.5 }}>
                {experiment.input_columns.map((col) => (
                  <Chip
                    key={col}
                    label={col}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: "0.75rem" }}
                  />
                ))}
              </Box>
            </Box>

            <Box sx={{ display: "flex", alignItems: "center" }}>
              <strong>Target column:</strong>
              <Chip
                label={experiment.output_columns[0]}
                size="small"
                color="primary"
                sx={{ ml: 1, fontSize: "0.75rem" }}
              />
            </Box>
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
