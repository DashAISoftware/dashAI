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
import { useTheme } from "@mui/material/styles";
import { getPredictionStatus } from "../../utils/predictionStatus";
import DatasetTable from "../notebooks/dataset/DatasetTable";
import { getDatasetFile } from "../../api/datasets";

const RUNNING_STATUSES = ["Delivered", "Started"];

function ResultsTable({ selectedPrediction }) {
  const theme = useTheme();
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
      <Typography variant="subtitle1" fontWeight={600}>
        Prediction Results
      </Typography>

      <Typography
        variant="subtitle2"
        sx={{ color: theme.palette.text.secondary, mb: 1, display: "block" }}
      >
        {loadingExecution
          ? "The prediction is still running. Results will be available once it is finished."
          : 'The table below displays a preview of the prediction results. You can download the full results as a CSV file using the "Download CSV" buttonbelow.'}
      </Typography>

      {/* Show loading indicator if prediction is running */}
      {loadingExecution && (
        <Box
          sx={{
            py: 4,
            textAlign: "center",
            color: theme.palette.text.secondary,
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
          <>
            <Typography
              variant="body2"
              sx={{ color: theme.palette.text.secondary, mb: 2 }}
            >
              {selectedPrediction.dataset
                ? `Based on dataset: ${selectedPrediction.dataset.name}`
                : "Manually provided input data."}
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
