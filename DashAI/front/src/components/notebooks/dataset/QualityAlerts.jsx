import React from "react";
import { Alert } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";

export const QualityAlerts = ({ qualityInfo, generalInfo }) => {
  if (!qualityInfo) return null;

  const alerts = [];

  // Duplicate rows
  if (generalInfo?.duplicate_rows > 0) {
    alerts.push(
      <Alert severity="warning" sx={{ mb: 1 }} key="duplicates">
        Found {generalInfo.duplicate_rows} duplicate rows in the dataset
      </Alert>,
    );
  }

  // High missing values
  const highNanColumns = Object.entries(qualityInfo.nan_ratio_per_column || {})
    .filter(([_, ratio]) => ratio > 0.1)
    .map(([col]) => col);

  if (highNanColumns.length > 0) {
    alerts.push(
      <Alert severity="warning" sx={{ mb: 1 }} key="nan">
        High missing values in: {highNanColumns.join(", ")}
      </Alert>,
    );
  }

  // High cardinality columns
  if (qualityInfo.high_cardinality_columns?.length > 0) {
    alerts.push(
      <Alert severity="info" sx={{ mb: 1 }} key="cardinality">
        High cardinality detected in:{" "}
        {qualityInfo.high_cardinality_columns.join(", ")}
      </Alert>,
    );
  }

  // No issues
  if (alerts.length === 0) {
    alerts.push(
      <Alert
        severity="success"
        sx={{ mb: 1 }}
        key="quality"
        icon={<CheckIcon />}
      >
        No data quality issues detected
      </Alert>,
    );
  }

  return <>{alerts}</>;
};
