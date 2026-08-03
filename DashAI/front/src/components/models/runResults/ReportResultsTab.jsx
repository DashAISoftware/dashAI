import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, CircularProgress, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

import { getReports, deleteReport } from "../../../api/report";
import { getComponents } from "../../../api/component";
import ReportCard from "../../reports/ReportCard";

/** Statuses that mean a report job is still outstanding. */
const IN_FLIGHT = [1, 2];

/** How often the list refreshes while any report is still computing. */
const POLL_INTERVAL_MS = 3000;

/**
 * Lists the evaluation reports created for a run, newest first. New ones
 * are added from the right sidebar, mirroring how explainers are added.
 */
export default function ReportResultsTab({ run, session, refreshTrigger }) {
  const { t } = useTranslation(["reports"]);
  const { enqueueSnackbar } = useSnackbar();

  const [reports, setReports] = useState([]);
  const [displayNames, setDisplayNames] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchReports = useCallback(async () => {
    try {
      const response = await getReports(run.id);
      setReports([...response].sort((a, b) => b.id - a.id));
    } catch (error) {
      console.error("Error fetching reports:", error);
      enqueueSnackbar(t("reports:error.fetch"), { variant: "error" });
    }
  }, [run.id, enqueueSnackbar, t]);

  useEffect(() => {
    setLoading(true);
    fetchReports().finally(() => setLoading(false));
  }, [fetchReports, refreshTrigger]);

  // Component display names are resolved once per task so each card can show a
  // human readable title instead of the registry key.
  useEffect(() => {
    if (!session?.task_name) return;
    getComponents({
      selectTypes: ["Report"],
      relatedComponent: session.task_name,
    })
      .then((components) =>
        setDisplayNames(
          Object.fromEntries(
            components.map((item) => [
              item.name,
              item.display_name || item.name,
            ]),
          ),
        ),
      )
      .catch((error) => console.error("Error fetching report names:", error));
  }, [session?.task_name]);

  const anyRunning = reports.some((item) => IN_FLIGHT.includes(item.status));

  useEffect(() => {
    if (!anyRunning) return undefined;
    const handle = setInterval(fetchReports, POLL_INTERVAL_MS);
    return () => clearInterval(handle);
  }, [anyRunning, fetchReports]);

  const handleDelete = async (report) => {
    try {
      await deleteReport(report.id);
      setReports((prev) => prev.filter((item) => item.id !== report.id));
    } catch (error) {
      console.error("Error deleting report:", error);
      enqueueSnackbar(t("reports:error.delete"), { variant: "error" });
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (reports.length === 0) {
    return (
      <Box sx={{ py: 6, textAlign: "center" }}>
        <Typography variant="body2" color="text.secondary">
          {t("reports:message.empty")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ py: 4, display: "flex", flexDirection: "column", gap: 3 }}>
      {reports.map((report) => (
        <ReportCard
          key={report.id}
          report={report}
          displayName={displayNames[report.report_name]}
          onDelete={handleDelete}
        />
      ))}
    </Box>
  );
}

ReportResultsTab.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
  }).isRequired,
  session: PropTypes.shape({
    task_name: PropTypes.string,
  }),
  refreshTrigger: PropTypes.number,
};
