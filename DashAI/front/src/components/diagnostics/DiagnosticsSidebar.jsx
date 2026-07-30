import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { Box, Typography, TextField, CircularProgress } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Search as SearchIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import { getComponents } from "../../api/component";
import ModelListItem from "../models/model/ModelListItem";
import InlineDiagnosticCreator from "./InlineDiagnosticCreator";
import { useModels } from "../models/ModelsContext";

const matchesQuery = (component, query) =>
  (component.display_name || component.name).toLowerCase().includes(query) ||
  (component.metadata?.description || "").toLowerCase().includes(query);

/**
 * Right-side panel shown while the model detail view is on its Diagnostics
 * tab. Lists the diagnostics compatible with the session's task, mirroring the
 * add-explainers sidebar; clicking one opens its creation dialog.
 */
export default function DiagnosticsSidebar({ run, session, onCreated }) {
  const theme = useTheme();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["models", "diagnostics"]);

  const [diagnostics, setDiagnostics] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const { diagnosticToCreate, openDiagnosticCreator, closeDiagnosticCreator } =
    useModels();

  const taskName = session?.task_name;

  const fetchDiagnostics = useCallback(async () => {
    if (!taskName) return;
    try {
      setLoading(true);
      const response = await getComponents({
        selectTypes: ["Diagnostic"],
        relatedComponent: taskName,
      });
      setDiagnostics(response);
    } catch (error) {
      console.error("Error fetching diagnostics:", error);
      enqueueSnackbar(t("diagnostics:error.fetch"), { variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [taskName, enqueueSnackbar, t]);

  useEffect(() => {
    fetchDiagnostics();
  }, [fetchDiagnostics]);

  const query = searchQuery.trim().toLowerCase();
  const filtered = query
    ? diagnostics.filter((item) => matchesQuery(item, query))
    : diagnostics;

  return (
    <SideBar>
      <Box
        sx={{
          p: 4,
          borderBottom: `1px solid ${theme.palette.ui.border}`,
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          height: 64,
        }}
      >
        <Typography variant="h6" color="text.primary">
          {t("diagnostics:label.availableDiagnostics")}
        </Typography>
      </Box>

      <Box sx={{ p: 4, flexShrink: 0 }}>
        <TextField
          fullWidth
          size="small"
          placeholder={t("diagnostics:label.searchDiagnostics")}
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <SearchIcon sx={{ mr: 2, color: "text.secondary" }} />
              ),
            },
          }}
        />
      </Box>

      <Box sx={{ flex: 1, overflowY: "auto", px: 4, pb: 4 }}>
        {loading ? (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: "100%",
            }}
          >
            <CircularProgress size={32} />
          </Box>
        ) : filtered.length === 0 ? (
          <Typography
            variant="body2"
            sx={{ color: "text.secondary", textAlign: "center", py: 2 }}
          >
            {searchQuery
              ? t("diagnostics:label.noDiagnosticsMatchSearch")
              : t("diagnostics:label.noCompatibleDiagnosticsFound")}
          </Typography>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {filtered.map((diagnostic) => (
              <ModelListItem
                key={diagnostic.name}
                model={diagnostic}
                onClick={() => openDiagnosticCreator(diagnostic)}
              />
            ))}
          </Box>
        )}
      </Box>

      {diagnosticToCreate && (
        <InlineDiagnosticCreator
          open
          runId={run.id}
          diagnosticName={diagnosticToCreate.name}
          displayName={diagnosticToCreate.display_name}
          onCreated={onCreated}
          onCancel={closeDiagnosticCreator}
        />
      )}
    </SideBar>
  );
}

DiagnosticsSidebar.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
  }).isRequired,
  session: PropTypes.shape({
    task_name: PropTypes.string,
  }),
  onCreated: PropTypes.func,
};
