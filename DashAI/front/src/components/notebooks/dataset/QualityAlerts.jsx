import React from "react";
import { Alert } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";

export const QualityAlerts = ({ qualityInfo, generalInfo, missingValues }) => {
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

  // Missing values
  if (Object.values(missingValues).some((value) => value > 0)) {
    alerts.push(
      <Alert severity="warning" sx={{ mb: 1 }} key="nan">
        Missing values detected in columns:{" "}
        {Object.entries(missingValues)
          .filter(([_, value]) => value > 0)
          .map(([key, _]) => key)
          .join(", ")}
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
