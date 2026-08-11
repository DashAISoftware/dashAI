import React, { useState, useEffect, useCallback } from "react";
import {
  Paper,
  Box,
  Typography,
  Tooltip,
  IconButton,
  CircularProgress,
} from "@mui/material";
import { useTheme, alpha } from "@mui/material/styles";
import { Analytics, Info, Delete } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import RunStatusDot from "../../shared/RunStatusDot";
import ArtifactViewer from "../../shared/ArtifactViewer";
import { getExplorerStatus } from "../../../utils/explorerStatus";
import { getComponentById } from "../../../api/component";
import {
  getExplorerById,
  resetExplorerResults,
  updateExplorerResults,
} from "../../../api/explorer";
import ExplorerInfoModal from "./ExplorerInfoModal";
import { useExplorerResults } from "./useExplorerResults";
import { useTranslation } from "react-i18next";

export default function ExplorerBox({
  explorer,
  handleExplorerDeleteClick,
  onStatusChange,
  isHighlighted = false,
}) {
  const { t } = useTranslation(["datasets", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [explorerComponent, setExplorerComponent] = useState({});
  const [openExplorerDetails, setOpenExplorerDetails] = useState(false);
  const { loading, artifact, error, fetchExplorerResults } =
    useExplorerResults(explorer);

  const statusLabel = explorer.status;

  const handleExplorerDetailsClick = () => {
    setOpenExplorerDetails(true);
  };

  const handleSaveEdit = useCallback(
    async (figure) => {
      try {
        await updateExplorerResults(explorer.id, artifact.index, figure);
        // Pull the artifact back with its `overridden` flag set, so the reset
        // button shows up straight away instead of only after a reopen.
        await fetchExplorerResults();
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
    [explorer.id, artifact, fetchExplorerResults, enqueueSnackbar, t],
  );

  const handleResetEdit = useCallback(async () => {
    try {
      await resetExplorerResults(explorer.id, artifact.index);
      // The stored artifact changed on the server, so pull the computed
      // figure back in rather than guessing it client side.
      await fetchExplorerResults();
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
  }, [explorer.id, artifact, fetchExplorerResults, enqueueSnackbar, t]);

  useEffect(() => {
    const fetchConverterComponent = async () => {
      try {
        const component = await getComponentById(explorer.exploration_type);
        setExplorerComponent(component);
      } catch (error) {
        console.error("Failed to fetch converter component:", error);
      }
    };

    fetchConverterComponent();
  }, [explorer.exploration_type, t]);

  useEffect(() => {
    let intervalId;

    const fetchExplorerStatus = async () => {
      try {
        const updatedExplorer = await getExplorerById(explorer.id);

        // 🔑 Notificar al padre si cambia el estado
        if (updatedExplorer.status !== explorer.status) {
          onStatusChange(updatedExplorer.id, updatedExplorer.status);
        }

        const status = updatedExplorer.status;
        if (status === 3 || status === 4) {
          // Finished or Error
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Failed to fetch explorer status:", error);
        clearInterval(intervalId);
      }
    };

    const currentStatus = explorer.status;
    if (currentStatus !== 3 && currentStatus !== 4) {
      //  Not Finished and not Error
      intervalId = setInterval(fetchExplorerStatus, 1500);
    }

    return () => clearInterval(intervalId);
  }, [explorer.id, explorer.status, onStatusChange]);

  return (
    <Paper
      key={explorer.id}
      variant="outlined"
      className="explorer-box"
      sx={{
        p: 4,
        bgcolor: "background.paper",
        borderColor: theme.palette.ui.border,
        borderRadius: 1,
        height: "100%",
        position: "relative",
        zIndex: isHighlighted ? 1 : 0,
        "@keyframes newItemHighlight": {
          "0%": { boxShadow: "none" },
          "20%": {
            boxShadow: `0 0 0 3px ${alpha(
              theme.palette.primary.main,
              0.65,
            )}, 0 0 24px 8px ${alpha(theme.palette.primary.main, 0.2)}`,
          },
          "100%": { boxShadow: "none" },
        },
        animation: isHighlighted
          ? "newItemHighlight 4s ease-in-out forwards"
          : "none",
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 4,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Analytics
              sx={{ color: theme.palette.primary.main, fontSize: 20 }}
            />
            <Typography variant="h6">
              {explorerComponent.display_name ??
                explorer.exploration_type ??
                t("datasets:unknownComponent")}
            </Typography>
            <Tooltip title={getExplorerStatus(statusLabel, t)}>
              <span>
                <RunStatusDot status={statusLabel} />
              </span>
            </Tooltip>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {statusLabel === 3 && ( // Finished
              <Tooltip title={t("common:info")}>
                <IconButton
                  size="small"
                  aria-label="info"
                  onClick={handleExplorerDetailsClick}
                >
                  <Info fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            {(statusLabel === 4 || statusLabel === 3) && ( // Error or Finished
              <IconButton
                size="small"
                aria-label="delete"
                color="error"
                onClick={() => handleExplorerDeleteClick(explorer)}
              >
                <Delete fontSize="small" />
              </IconButton>
            )}
          </Box>
        </Box>

        {statusLabel === 3 ? ( // Finished
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            {loading && (
              <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
                <CircularProgress size={24} />
              </Box>
            )}
            {!loading && error && (
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", textAlign: "center", p: 2 }}
              >
                {t("datasets:error.explorerResultsUnavailable")}
              </Typography>
            )}
            {!loading && !error && artifact && (
              <ArtifactViewer
                artifact={artifact}
                onSaveEdit={handleSaveEdit}
                onResetEdit={handleResetEdit}
                canReset={Boolean(artifact.overridden)}
              />
            )}
          </Box>
        ) : statusLabel === 4 ? ( // Error
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: theme.palette.background.default,
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              p: 4,
            }}
          >
            <Typography
              variant="body2"
              sx={{ color: "error.main", textAlign: "center" }}
            >
              {t("datasets:error.explorerFailed")}
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: theme.palette.ui.hover,
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <CircularProgress size={24} sx={{ mr: 2 }} />
            <Typography>{t("common:processing")}</Typography>
          </Box>
        )}
        {openExplorerDetails && (
          <ExplorerInfoModal
            open={openExplorerDetails}
            onClose={() => {
              setOpenExplorerDetails(false);
            }}
            explorer={explorer}
            explorerComponent={explorerComponent}
          />
        )}
      </Box>
    </Paper>
  );
}
