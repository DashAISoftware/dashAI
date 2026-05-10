import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
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

import { TabColumns, TabResults, TabParameters } from "./tabs";
import PlotLayoutForm from "./plotLayout/PlotLayoutForm";
import { updateExplorerResults } from "../../../api/explorer";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { formatDate } from "../../../utils";

export default function ExplorerDetailsModal({
  open = false,
  onClose = () => {},
  explorer,
  explorerComponent,
  data,
  setData,
  dataType,
  loading,
}) {
  const [currentTab, setCurrentTab] = useState(0);
  const [localData, setLocalData] = useState(data);
  const [formReady, setFormReady] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);

  const localDataRef = useRef(localData);
  localDataRef.current = localData;

  // Sync data prop → localData when data arrives after mount (explorer results load async)
  useEffect(() => {
    if (data && !localData) {
      setLocalData(data);
    }
  }, [data, localData]);

  useEffect(() => {
    startTransition(() => setFormReady(true));
  }, []);

  if (!explorer) return null;
  if (!data) return null;

  const tabs = [
    { label: t("common:results"), value: 0, icon: <AnalyticsOutlined /> },
    { label: t("common:info"), value: 1, icon: <InfoOutlined /> },
  ];

  const handleTabChange = (_, newValue) => {
    startTransition(() => setCurrentTab(newValue));
  };

  const handleSaveChangesLayout = useCallback(async () => {
    const current = localDataRef.current;
    try {
      await updateExplorerResults(explorer.id, current);
      setData(current);
      enqueueSnackbar(
        t("datasets:message.explorerResultsUpdatedSuccessfully"),
        { variant: "success" },
      );
    } catch (error) {
      console.error("Failed to update explorer results:", error);
      enqueueSnackbar(t("datasets:error.failedToUpdateExplorerResults"), {
        variant: "error",
      });
    }
  }, [explorer.id, setData, enqueueSnackbar, t]);

  const handleSetData = useCallback((newData) => {
    setLocalData((prev) => ({ ...prev, data: newData }));
  }, []);

  const handleSetLayout = useCallback((newLayout) => {
    setLocalData((prev) => ({ ...prev, layout: newLayout }));
  }, []);

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
                  <Typography
                    sx={{
                      fontFamily: '"IBM Plex Mono", monospace',
                      fontSize: "0.78rem",
                    }}
                    color="text.primary"
                  >
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
                  <TabParameters data={explorer.parameters} />
                </Box>
              </Box>
            </Box>
          )}

          {/* Results tab: always mounted to preserve state */}
          <Box
            sx={{
              display: currentTab === 0 ? "flex" : "none",
              flexDirection: { xs: "column", xl: "row" },
              height: "100%",
              overflow: "auto",
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
            {formReady && (
              <>
                <Box
                  sx={{
                    flex: { xs: "0 0 auto", xl: 1 },
                    minWidth: 0,
                    minHeight: { xs: "auto", xl: 0 },
                    justifyContent: "center",
                    alignItems: "center",
                    overflow: { xs: "visible", xl: "auto" },
                    p: 4,
                  }}
                >
                  <TabResults
                    id={explorer.id}
                    data={localData}
                    dataType={dataType}
                    loading={loading}
                  />
                </Box>

                {dataType === "plotly_json" && (
                  <Box
                    sx={{
                      width: { xs: "100%", xl: "50%" },
                      flexShrink: 0,
                      overflowY: { xs: "visible", xl: "auto" },
                      mt: { xs: 4, xl: 0 },
                    }}
                  >
                    <PlotLayoutForm
                      data={localData.data}
                      setData={handleSetData}
                      layout={localData.layout}
                      setLayout={handleSetLayout}
                      onSave={handleSaveChangesLayout}
                    />
                  </Box>
                )}
              </>
            )}
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
