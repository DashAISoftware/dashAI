import React, { useEffect, useState, useCallback } from "react";
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
} from "@mui/material";
import { getPredictionStatus } from "../../utils/predictionStatus";
import DatasetTable from "../notebooks/dataset/DatasetTable";
import { getDatasetFile } from "../../api/datasets";
import { useTranslation } from "react-i18next";

const RUNNING_STATUSES = [1, 2]; // Delivered or Started

function ResultsTable({ selectedPrediction }) {
  const [loadingExecution, setLoadingExecution] = useState(
    RUNNING_STATUSES.includes(getPredictionStatus(selectedPrediction?.status)),
  );
  const { t } = useTranslation(["prediction"]);

  const fetchPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(
        selectedPrediction.results_path,
        page,
        pageSize,
      );
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [selectedPrediction],
  );

  useEffect(() => {
    if (!selectedPrediction) return;
    setLoadingExecution(
      RUNNING_STATUSES.includes(
        getPredictionStatus(selectedPrediction?.status),
      ),
    );
  }, [selectedPrediction]);

  return (
    <Box>
      <Typography variant="subtitle1" fontWeight={600}>
        {t("prediction:label.predictionResults")}
      </Typography>

      <Typography
        variant="subtitle2"
        color="text.secondary"
        sx={{ mb: 1, display: "block" }}
      >
        {loadingExecution
          ? t("prediction:label.predictionStillRunningResults")
          : t("prediction:label.resultsPreviewDownloadInfo")}
      </Typography>

      {/* Show loading indicator if prediction is running */}
      {loadingExecution && (
        <Box
          sx={{
            py: 4,
            textAlign: "center",
            color: "text.secondary",
          }}
        >
          <CircularProgress size={28} />
          <Typography variant="body2" sx={{ mt: 1 }}>
            {t("prediction:label.predictionStillRunning")}
          </Typography>
        </Box>
      )}

      {!loadingExecution &&
        selectedPrediction &&
        selectedPrediction?.status === 3 && ( // Finished
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {selectedPrediction.dataset
                ? t("prediction:label.basedOnDataset", {
                    datasetName: selectedPrediction.dataset.name,
                  })
                : t("prediction:label.manuallyProvidedInputData")}
            </Typography>
            <Paper>
              <DatasetTable
                fetchPage={fetchPage}
                initialPageSize={10}
                autoHeight={true}
                slots={{ toolbar: null }}
                datasetPath={selectedPrediction.results_path}
              />
            </Paper>
          </>
        )}
    </Box>
  );
}

export default ResultsTable;
