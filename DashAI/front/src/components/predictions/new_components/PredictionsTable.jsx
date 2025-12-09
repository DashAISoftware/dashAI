import React from "react";
import {
  Box,
  Chip,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
} from "@mui/material";
import { formatDate, getColorByStatus } from "../../../utils";
import { getPredictionStatus } from "../../../utils/predictionStatus";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";

function PredictionsTable({ history, onItemClick }) {
  if (!history || history.length === 0) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <Typography color="text.secondary">No predictions yet</Typography>
        <Typography variant="caption" color="text.secondary">
          Run your first prediction to see it here
        </Typography>
      </Box>
    );
  }

  const computeDuration = (start, end) => {
    if (!start || !end) return "–";

    const startTime = new Date(start);

    const endTime = end ? new Date(end) : new Date();
    const diffMs = endTime - startTime;

    if (diffMs < 0) return "–";

    const seconds = Math.floor(diffMs / 1000);
    return `${seconds}s`;
  };

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            <TableCell>Created</TableCell>
            <TableCell>Time</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {history.map((item) => {
            const statusText = getPredictionStatus(item.status);

            return (
              <TableRow
                key={item.id}
                hover
                onClick={() => onItemClick(item)}
                sx={{ cursor: "pointer" }}
              >
                {/* TYPE */}
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>
                    {item.type ?? "—"}
                  </Typography>
                </TableCell>

                {/* CREATED */}
                <TableCell>{formatDate(item.created)}</TableCell>

                {/* TIME (end - start) */}
                <TableCell>
                  {computeDuration(item.start_time, item.end_time)}
                </TableCell>

                {/* STATUS */}
                <TableCell>
                  <Chip
                    icon={
                      statusText === "Finished" ? (
                        <CheckCircleIcon />
                      ) : statusText === "Failed" ? (
                        <ErrorOutlineIcon />
                      ) : (
                        <CircularProgress size={12} />
                      )
                    }
                    label={statusText}
                    size="small"
                    sx={{ bgcolor: getColorByStatus(statusText) }}
                  />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default PredictionsTable;
