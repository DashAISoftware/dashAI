import React, { useCallback, useEffect, useState } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Paper,
  Alert,
  Chip,
} from "@mui/material";
import DatasetTable from "../notebooks/dataset/DatasetTable";
import {
  getDatasetFile,
  getDatasetFileFiltered,
  getDatasetTypesByFilePath,
} from "../../api/datasets";
import { formatDate } from "../../pages/results/constants/formatDate";
import { useTranslation } from "react-i18next";

function DatasetSelector({
  experiment,
  datasets,
  selectedDataset,
  setSelectedDataset,
  actionSlot = null,
}) {
  const { t } = useTranslation(["prediction", "common", "datasets"]);
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
    <Box sx={{ mb: 6 }}>
      <Box sx={{ display: "flex", alignItems: "stretch", gap: 2 }}>
        <Autocomplete
          sx={{ flex: 1 }}
          options={datasets}
          getOptionLabel={(option) => option.name}
          isOptionEqualToValue={(opt, val) => opt.id === val.id}
          value={selectedDataset}
          onChange={(_, newValue) => setSelectedDataset(newValue)}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("prediction:label.selectDataset")}
              variant="outlined"
              placeholder={t("datasets:label.typeToSearchDatasets")}
            />
          )}
          renderOption={(props, option) => {
            const { key, ...rootProps } = props;
            return (
              <Box component="li" key={key} {...rootProps}>
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    width: "100%",
                    gap: 0.25,
                  }}
                >
                  <Typography variant="body1" fontWeight="medium">
                    {option.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t("common:created")}: {formatDate(option.created)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("datasets:label.rowsColumnsInfo", {
                      totalRows: option.total_rows ?? "...",
                      totalColumns: option.total_columns ?? "...",
                    })}
                  </Typography>
                </Box>
              </Box>
            );
          }}
        />
        {actionSlot}
      </Box>
      {selectedDataset && (
        <>
          <Alert severity="info" sx={{ mt: 4 }}>
            <Typography variant="h5" sx={{ mb: 2 }}>
              {t("prediction:label.predictionInfo")}
            </Typography>

            <Box sx={{ mb: 2 }}>
              <strong>{t("prediction:label.inputColumns")}:</strong>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mt: 1 }}>
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
                sx={{ ml: 2, fontSize: "0.75rem" }}
              />
            </Box>
          </Alert>

          <Paper>
            <DatasetTable
              fetchPage={fetchDatasetPage}
              initialPageSize={5}
              datasetPath={selectedDataset.file_path}
              columnTypes={columnTypes}
              showExportButton={false}
            />
          </Paper>
        </>
      )}
    </Box>
  );
}

export default DatasetSelector;
