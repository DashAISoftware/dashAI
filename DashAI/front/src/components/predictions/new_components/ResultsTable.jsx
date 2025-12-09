import React, { useEffect, useState } from "react";
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

function ResultsTable({ selectedPrediction }) {
  const [results, setResults] = useState([]);
  const [inputColumns, setInputColumns] = useState([]);
  const [loadingExecution, setLoadingExecution] = useState(false);

  const title = "Prediction Results";
  const subtitle = "Sample of up to 50 prediction rows";

  const RUNNING_STATUSES = ["Delivered", "Started"];

  useEffect(() => {
    if (!selectedPrediction) return;
    console.log("Selected Prediction changed:", selectedPrediction);

    // If prediction is running, show loading
    if (
      RUNNING_STATUSES.includes(getPredictionStatus(selectedPrediction.status))
    ) {
      setLoadingExecution(true);
      setResults([]);
      return;
    }

    setLoadingExecution(false);

    const fetchData = async () => {
      try {
        const response = await getPredictionSummary(selectedPrediction.id);

        const sampleData = response.sample_data || [];
        setResults(sampleData);

        if (sampleData.length > 0) {
          const firstInput = sampleData[0].input || {};
          setInputColumns(Object.keys(firstInput));
        }
      } catch (error) {
        console.error("Error fetching prediction summary:", error);
      }
    };

    fetchData();
  }, [selectedPrediction]);

  return (
    <Box>
      <Typography variant="subtitle2" fontWeight={600}>
        {title}
      </Typography>

      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mb: 2, display: "block" }}
      >
        {subtitle}
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

      {!loadingExecution && (
        <TableContainer component={Paper} sx={{ maxHeight: 500 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>

                {inputColumns.map((column) => (
                  <TableCell key={column}>{column}</TableCell>
                ))}

                <TableCell
                  sx={{
                    bgcolor: "success.light",
                    color: "success.dark",
                    fontWeight: 600,
                  }}
                >
                  Prediction
                </TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {results.map((result, index) => (
                <TableRow key={index} hover>
                  <TableCell>{index + 1}</TableCell>

                  {inputColumns.map((column) => (
                    <TableCell key={column}>
                      {result.input?.[column] ?? "-"}
                    </TableCell>
                  ))}

                  <TableCell
                    sx={{
                      bgcolor: "success.light",
                      fontWeight: 600,
                      color: "success.dark",
                    }}
                  >
                    {result.value}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}

export default ResultsTable;
