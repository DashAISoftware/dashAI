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
import { getPredictionSummary } from "../../../api/predict";
import { getPredictionStatus } from "../../../utils/predictionStatus";
import DatasetTable from "../../notebooks/dataset/DatasetTable";
import { getDatasetFile } from "../../../api/datasets";

const RUNNING_STATUSES = ["Delivered", "Started"];

function ResultsTable({ selectedPrediction }) {
  const [loadingExecution, setLoadingExecution] = useState(
    RUNNING_STATUSES.includes(getPredictionStatus(selectedPrediction?.status)),
  );

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
      <Typography variant="subtitle2" fontWeight={600}>
        Prediction Results
      </Typography>

      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mb: 2, display: "block" }}
      >
        View of the entire prediction results once the prediction is completed.
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
            Prediction is still running...
          </Typography>
        </Box>
      )}

      {!loadingExecution &&
        selectedPrediction &&
        getPredictionStatus(selectedPrediction?.status) === "Finished" && (
          <Paper>
            <DatasetTable
              fetchPage={fetchPage}
              initialPageSize={10}
              autoHeight={true}
              slots={{ toolbar: null }}
            />
          </Paper>
        )}
    </Box>
  );
}

export default ResultsTable;
