import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { Box, Typography, TextField, CircularProgress } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Search as SearchIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import { getComponents } from "../../api/component";
import ModelListItem from "./model/ModelListItem";
import {
  startComponentDownload,
  subscribeAnyDownloadState,
} from "./model/ComponentDownloadControl";
import ModelDownloadStatusIcon from "./model/ModelDownloadStatusIcon";
import { useTranslation } from "react-i18next";
import { useTourContext } from "../tour/TourProvider";
import { useModels } from "./ModelsContext";
import AddModelDialog from "./AddModelDialog";
import ColumnInsights from "../notebooks/dataset/ColumnInsights";

export default function ModelsRightBar({ onToggle }) {
  const theme = useTheme();
  const [models, setModels] = useState([]);
  const [filteredModels, setFilteredModels] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["models", "common"]);

  const {
    selectedSession: session,
    onRunCreated,
    runs: existingRuns,
    selectModel,
    configOpen,
    selectedModel,
    closeConfig,
    datasetInfo,
    setDatasetTab,
    sessionRightContent,
  } = useModels();

  const fetchModels = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await getComponents({
        selectTypes: ["Model"],
        relatedComponent: session.task_name,
      });
      setModels(response);
      setFilteredModels(response);
    } catch (error) {
      console.error("Error fetching models:", error);
      enqueueSnackbar(t("models:error.fetchingModels"), {
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  }, [session?.task_name, enqueueSnackbar, t]);

  useEffect(() => {
    if (session) {
      fetchModels();
    } else {
      setModels([]);
      setFilteredModels([]);
      setSearchQuery("");
    }
  }, [session, fetchModels]);

  // Refetch when any download finishes (or is deleted) so the row's disabled
  // state, which is derived from the fetched model list, stays in sync. The
  // download may have been started by a previous mount of this panel, so we
  // cannot rely on that download's onStatusChange callback firing here.
  useEffect(() => {
    if (!session) return undefined;
    return subscribeAnyDownloadState((_name, state) => {
      if (state.downloaded !== undefined) fetchModels();
    });
  }, [session, fetchModels]);

  // Filter models based on search
  useEffect(() => {
    if (searchQuery.trim() === "") {
      setFilteredModels(models);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredModels(
        models.filter(
          (model) =>
            (model.display_name || model.name).toLowerCase().includes(query) ||
            (model.metadata?.description || "").toLowerCase().includes(query),
        ),
      );
    }
  }, [searchQuery, models]);

  const tourContext = useTourContext();

  const handleModelClick = (model) => {
    if (!session) {
      enqueueSnackbar(t("models:error.selectSessionFirst"), {
        variant: "warning",
      });
      return;
    }
    // A download-required model that has not been downloaded cannot be
    // configured; it is blocked in the list with an inline download control.
    if (model.metadata?.requires_download && !model.downloaded) {
      startComponentDownload({
        component: model,
        enqueueSnackbar,
        t,
        onStatusChange: () => fetchModels(),
      });
      return;
    }
    selectModel(model);
    if (tourContext?.run && tourContext?.stepIndex === 2) {
      const waitForElement = () => {
        const element = document.querySelector('[data-tour="model-config"]');
        if (element) {
          tourContext.nextStep();
        } else {
          setTimeout(waitForElement, 100);
        }
      };
      setTimeout(waitForElement, 300);
    }
  };

  if (sessionRightContent) {
    return (
      <SideBar>
        <Box
          sx={{
            p: 2,
            borderBottom: `1px solid ${theme.palette.ui.border}`,
            flexShrink: 0,
            height: 64,
            display: "flex",
            alignItems: "center",
          }}
        >
          <Typography variant="h6" color="text.primary">
            {t("models:label.configureSession")}
          </Typography>
        </Box>
        <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
          {sessionRightContent}
        </Box>
      </SideBar>
    );
  }

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          height: "100%",
          width: "100%",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 2,
            borderBottom: `1px solid ${theme.palette.ui.border}`,
            flexShrink: 0,
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-start",
          }}
        >
          <Typography variant="h6" color="text.primary">
            {t("models:label.availableModels")}
          </Typography>
        </Box>

        {/* Content */}
        {!session ? (
          datasetInfo ? (
            <Box sx={{ flex: 1, overflowY: "auto" }}>
              <ColumnInsights
                numericStats={datasetInfo?.numeric_stats}
                textStats={datasetInfo?.text_stats}
                onNavigateTab={setDatasetTab}
              />
            </Box>
          ) : (
            <Box
              sx={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                p: 2,
              }}
            >
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", textAlign: "center" }}
              >
                {t("models:label.selectSessionToViewModels")}
              </Typography>
            </Box>
          )
        ) : (
          <>
            {/* Search Box */}
            <Box sx={{ p: 4, flexShrink: 0 }}>
              <TextField
                fullWidth
                size="small"
                placeholder={t("models:label.searchModels")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                slotProps={{
                  input: {
                    startAdornment: (
                      <SearchIcon sx={{ mr: 2, color: "text.secondary" }} />
                    ),
                  },
                }}
              />
            </Box>

            {/* Models List */}
            <Box sx={{ flex: 1, overflow: "auto", p: 4 }}>
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
              ) : filteredModels.length === 0 ? (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    height: "100%",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ color: "text.secondary", textAlign: "center" }}
                  >
                    {searchQuery
                      ? t("models:label.noModelsMatchSearch")
                      : t("models:label.noCompatibleModelsFound")}
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {filteredModels.map((model, index) => {
                    const requiresDownload = Boolean(
                      model.metadata?.requires_download,
                    );
                    const needsDownload = requiresDownload && !model.downloaded;
                    return (
                      <ModelListItem
                        key={model.name}
                        model={model}
                        disabled={needsDownload}
                        onClick={() => handleModelClick(model)}
                        onDisabledClick={() => handleModelClick(model)}
                        data-tour={index === 0 ? "first-model" : undefined}
                        action={
                          requiresDownload ? (
                            <ModelDownloadStatusIcon
                              model={model}
                              onChanged={() => fetchModels()}
                            />
                          ) : null
                        }
                      />
                    );
                  })}
                </Box>
              )}
            </Box>
          </>
        )}
      </Box>
      {/* Modal de modelo */}
      <AddModelDialog
        open={configOpen}
        onClose={closeConfig}
        preselectedModel={selectedModel?.name}
        preselectedModelObject={selectedModel}
        session={session}
        existingRuns={existingRuns}
        onRunCreated={onRunCreated}
      />
    </SideBar>
  );
}

ModelsRightBar.propTypes = {
  onToggle: PropTypes.func.isRequired,
};
