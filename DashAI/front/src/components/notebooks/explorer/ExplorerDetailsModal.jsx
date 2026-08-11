import React, {
  useState,
  useEffect,
  useCallback,
  startTransition,
} from "react";
import {
  Tabs,
  Tab,
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Typography,
  Divider,
  CircularProgress,
} from "@mui/material";

import {
  InfoOutlined,
  AnalyticsOutlined,
  Close as CloseIcon,
} from "@mui/icons-material";

import { TabColumns, TabParameters } from "./tabs";
import ArtifactViewer from "../../shared/ArtifactViewer";
import {
  resetExplorerResults,
  updateExplorerResults,
} from "../../../api/explorer";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { formatDate } from "../../../utils";

export default function ExplorerDetailsModal({
  open = false,
  onClose = () => {},
  explorer,
  explorerComponent,
  artifact = null,
  error = null,
  onRefetch = () => {},
}) {
  const [currentTab, setCurrentTab] = useState(0);
  const [formReady, setFormReady] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);

  useEffect(() => {
    startTransition(() => setFormReady(true));
  }, []);

  if (!explorer) return null;
  if (!artifact) return null;

  const tabs = [
    { label: t("common:results"), value: 0, icon: <AnalyticsOutlined /> },
    { label: t("common:info"), value: 1, icon: <InfoOutlined /> },
  ];

  const handleTabChange = (_, newValue) => {
    startTransition(() => setCurrentTab(newValue));
  };

  const handleSaveEdit = useCallback(
    async (figure) => {
      try {
        await updateExplorerResults(explorer.id, artifact.index, figure);
        // Pull the artifact back with its `overridden` flag set, so the reset
        // button shows up straight away instead of only after a reopen.
        await onRefetch();
        enqueueSnackbar(
          t("datasets:message.explorerResultsUpdatedSuccessfully"),
          { variant: "success" },
        );
      } catch (err) {
        console.error("Failed to update explorer results:", err);
        enqueueSnackbar(t("datasets:error.failedToUpdateExplorerResults"), {
          variant: "error",
        });
        // Rethrow so ArtifactViewer does not treat the edit as saved.
        throw err;
      }
    },
    [explorer.id, artifact, onRefetch, enqueueSnackbar, t],
  );

  const handleResetEdit = useCallback(async () => {
    try {
      await resetExplorerResults(explorer.id, artifact.index);
      // The stored artifact changed on the server, so pull the computed
      // figure back in rather than guessing it client side.
      await onRefetch();
      enqueueSnackbar(
        t("datasets:message.explorerResultsRestoredSuccessfully"),
        { variant: "success" },
      );
    } catch (err) {
      console.error("Failed to reset explorer results:", err);
      enqueueSnackbar(t("datasets:error.failedToResetExplorerResults"), {
        variant: "error",
      });
    }
  }, [explorer.id, artifact, onRefetch, enqueueSnackbar, t]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      slotProps={{
        paper: {
          sx: {
            width: "90vw",
            height: "90vh",
            maxWidth: "none",
            m: "auto",
            display: "flex",
            flexDirection: "column",
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "ui.border",
          },
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          flexShrink: 0,
          bgcolor: "background.paper",
        }}
      >
        <Typography variant="h6" component="div">
          {t("datasets:label.detailsForExplorer", {
            name: explorerComponent.display_name,
          })}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        <IconButton onClick={onClose} aria-label={t("common:close")}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <Divider sx={{ flexShrink: 0 }} />

      <DialogContent
        sx={{
          p: 0,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          flex: 1,
          bgcolor: "background.paper",
        }}
      >
        {/* Tab bar */}
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          centered
          sx={{
            borderBottom: 1,
            borderColor: "divider",
            flexShrink: 0,
            bgcolor: "background.paper",
          }}
        >
          {tabs.map((tab) => (
            <Tab
              key={tab.value}
              value={tab.value}
              label={tab.label}
              icon={tab.icon}
            />
          ))}
        </Tabs>

        {/* Tab content */}
        <Box sx={{ flex: 1, overflow: "hidden", position: "relative" }}>
          {/* Details tab */}
          {currentTab === 1 && (
            <Box sx={{ p: 5, height: "100%", overflowY: "auto" }}>
              {/* Metadata strip */}
              {explorer.created && (
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    mb: 4,
                    pb: 3,
                    borderBottom: "1px solid",
                    borderColor: "ui.borderLight",
                  }}
                >
                  <Typography variant="sectionLabel" color="text.secondary">
                    {t("common:created")}
                  </Typography>
                  <Typography variant="code" color="text.primary">
                    {formatDate(explorer.created)}
                  </Typography>
                </Box>
              )}

              {/* Columns + Parameters side by side */}
              <Box
                sx={{
                  display: "flex",
                  gap: 6,
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                }}
              >
                <Box sx={{ flex: "1 1 240px", minWidth: 0 }}>
                  <TabColumns data={explorer.columns} />
                </Box>
                <Box sx={{ flex: "1 1 240px", minWidth: 0 }}>
                  <TabParameters
                    data={explorer.parameters}
                    schema={explorerComponent?.schema}
                  />
                </Box>
              </Box>
            </Box>
          )}

          {/* Results tab: always mounted to preserve state */}
          <Box
            sx={{
              display: currentTab === 0 ? "flex" : "none",
              flexDirection: "column",
              height: "100%",
              overflow: "auto",
              p: 4,
            }}
          >
            {!formReady && (
              <CircularProgress
                sx={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                }}
              />
            )}
            {formReady && !error && (
              <ArtifactViewer
                artifact={artifact}
                onSaveEdit={handleSaveEdit}
                onResetEdit={handleResetEdit}
                canReset={Boolean(artifact.overridden)}
              />
            )}
            {formReady && error && (
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", textAlign: "center", p: 2 }}
              >
                {t("datasets:error.explorerResultsUnavailable")}
              </Typography>
            )}
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
