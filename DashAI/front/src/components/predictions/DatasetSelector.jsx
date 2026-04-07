import React, { useCallback, useEffect, useState } from "react";
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
import MrtDatasetTable from "../notebooks/dataset/MrtDatasetTable";
import {
  getDatasetFile,
  getDatasetFileFiltered,
  getDatasetTypesByFilePath,
} from "../../api/datasets";
import { useTranslation } from "react-i18next";

function DatasetSelector({
  experiment,
  datasets,
  selectedDataset,
  setSelectedDataset,
}) {
  const { t } = useTranslation(["prediction", "common"]);
  const [columnTypes, setColumnTypes] = useState({});

  useEffect(() => {
    if (!selectedDataset?.file_path) return;
    getDatasetTypesByFilePath(selectedDataset.file_path)
      .then(setColumnTypes)
      .catch(() => {});
  }, [selectedDataset?.file_path]);

  const fetchDatasetPage = useCallback(
    async (page, pageSize, filterModel, sortModel) => {
      const hasFilters =
        filterModel?.items?.length > 0 || (sortModel && sortModel.length > 0);
      const data = hasFilters
        ? await getDatasetFileFiltered(
            selectedDataset.file_path,
            page,
            pageSize,
            filterModel,
            sortModel,
          )
        : await getDatasetFile(selectedDataset.file_path, page, pageSize);
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [selectedDataset],
  );

  return (
    <Box sx={{ mb: 3 }}>
      <FormControl fullWidth>
        <InputLabel>{t("prediction:label.selectDataset")}</InputLabel>
        <Select
          value={selectedDataset?.id || ""}
          label={t("prediction:label.selectDataset")}
          onChange={(e) => {
            const dataset = datasets.find((d) => d.id === e.target.value);
            setSelectedDataset(dataset);
          }}
        >
          {datasets.map((dataset) => (
            <MenuItem key={dataset.id} value={dataset.id}>
              {dataset.name} ({dataset.total_rows} {t("common:rows")})
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {selectedDataset && (
        <>
          <Alert severity="info" sx={{ mt: 2 }}>
            <Box sx={{ fontWeight: 600, mb: 1, fontSize: "1rem" }}>
              {t("prediction:label.predictionInfo")}
            </Box>

            <Box sx={{ mb: 1 }}>
              <strong>{t("prediction:label.inputColumns")}:</strong>
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
              <strong>{t("prediction:label.targetColumn")}:</strong>
              <Chip
                label={experiment.output_columns[0]}
                size="small"
                color="primary"
                sx={{ ml: 1, fontSize: "0.75rem" }}
              />
            </Box>
          </Alert>

          <Paper>
            <MrtDatasetTable
              fetchPage={fetchDatasetPage}
              initialPageSize={10}
              datasetPath={selectedDataset.file_path}
              columnTypes={columnTypes}
            />
          </Paper>
        </>
      )}
    </Box>
  );
}

export default DatasetSelector;
