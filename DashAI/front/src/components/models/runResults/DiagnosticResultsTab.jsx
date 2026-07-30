import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, CircularProgress, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

import { getDiagnostics, deleteDiagnostic } from "../../../api/diagnostic";
import { getComponents } from "../../../api/component";
import DiagnosticCard from "../../diagnostics/DiagnosticCard";

/** Statuses that mean a diagnostic job is still outstanding. */
const IN_FLIGHT = [1, 2];

/** How often the list refreshes while any diagnostic is still computing. */
const POLL_INTERVAL_MS = 3000;

/**
 * Lists the evaluation diagnostics created for a run, newest first. New ones
 * are added from the right sidebar, mirroring how explainers are added.
 */
export default function DiagnosticResultsTab({ run, session, refreshTrigger }) {
  const { t } = useTranslation(["diagnostics"]);
  const { enqueueSnackbar } = useSnackbar();

  const [diagnostics, setDiagnostics] = useState([]);
  const [displayNames, setDisplayNames] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchDiagnostics = useCallback(async () => {
    try {
      const response = await getDiagnostics(run.id);
      setDiagnostics([...response].sort((a, b) => b.id - a.id));
    } catch (error) {
      console.error("Error fetching diagnostics:", error);
      enqueueSnackbar(t("diagnostics:error.fetch"), { variant: "error" });
    }
  }, [run.id, enqueueSnackbar, t]);

  useEffect(() => {
    setLoading(true);
    fetchDiagnostics().finally(() => setLoading(false));
  }, [fetchDiagnostics, refreshTrigger]);

  // Component display names are resolved once per task so each card can show a
  // human readable title instead of the registry key.
  useEffect(() => {
    if (!session?.task_name) return;
    getComponents({
      selectTypes: ["Diagnostic"],
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
      .catch((error) =>
        console.error("Error fetching diagnostic names:", error),
      );
  }, [session?.task_name]);

  const anyRunning = diagnostics.some((item) =>
    IN_FLIGHT.includes(item.status),
  );

  useEffect(() => {
    if (!anyRunning) return undefined;
    const handle = setInterval(fetchDiagnostics, POLL_INTERVAL_MS);
    return () => clearInterval(handle);
  }, [anyRunning, fetchDiagnostics]);

  const handleDelete = async (diagnostic) => {
    try {
      await deleteDiagnostic(diagnostic.id);
      setDiagnostics((prev) =>
        prev.filter((item) => item.id !== diagnostic.id),
      );
    } catch (error) {
      console.error("Error deleting diagnostic:", error);
      enqueueSnackbar(t("diagnostics:error.delete"), { variant: "error" });
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (diagnostics.length === 0) {
    return (
      <Box sx={{ py: 6, textAlign: "center" }}>
        <Typography variant="body2" color="text.secondary">
          {t("diagnostics:message.empty")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ py: 4, display: "flex", flexDirection: "column", gap: 3 }}>
      {diagnostics.map((diagnostic) => (
        <DiagnosticCard
          key={diagnostic.id}
          diagnostic={diagnostic}
          displayName={displayNames[diagnostic.diagnostic_name]}
          onDelete={handleDelete}
        />
      ))}
    </Box>
  );
}

DiagnosticResultsTab.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
  }).isRequired,
  session: PropTypes.shape({
    task_name: PropTypes.string,
  }),
  refreshTrigger: PropTypes.number,
};
