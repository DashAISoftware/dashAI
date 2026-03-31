import React from "react";
import { Alert } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import { useTranslation } from "react-i18next";

export const QualityAlerts = ({ qualityInfo, generalInfo, missingValues }) => {
  const { t } = useTranslation(["datasets"]);
  if (!qualityInfo) return null;

  const alerts = [];

  // Duplicate rows
  if (generalInfo?.duplicate_rows > 0) {
    alerts.push(
      <Alert severity="warning" sx={{ mb: 1 }} key="duplicates">
        {t("datasets:label.foundDuplicateRows", {
          count: generalInfo.duplicate_rows,
        })}
      </Alert>,
    );
  }

  // Missing values
  if (Object.values(missingValues).some((value) => value > 0)) {
    alerts.push(
      <Alert severity="warning" sx={{ mb: 1 }} key="nan">
        {t("datasets:label.missingValuesDetected", {
          columns: Object.entries(missingValues)
            .filter(([_, value]) => value > 0)
            .map(([key, _]) => key)
            .join(", "),
        })}
      </Alert>,
    );
  }

  // High cardinality columns
  if (qualityInfo.high_cardinality_columns?.length > 0) {
    alerts.push(
      <Alert severity="info" sx={{ mb: 1 }} key="cardinality">
        {t("datasets:label.highCardinalityDetected", {
          columns: qualityInfo.high_cardinality_columns.join(", "),
        })}
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
        {t("datasets:label.noDataQualityIssuesDetected")}
      </Alert>,
    );
  }

  return <>{alerts}</>;
};
