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
  ViewColumnOutlined,
  TuneOutlined,
  AnalyticsOutlined,
  Close as CloseIcon,
} from "@mui/icons-material";

import { TabColumns, TabResults, TabInfo, TabParameters } from "./tabs";
import PlotLayoutForm from "./plotLayout/PlotLayoutForm";
import { updateExplorerResults } from "../../../api/explorer";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

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
  const [currentTab, setCurrentTab] = useState(3);
  const [localData, setLocalData] = useState(data);
  const [formReady, setFormReady] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);

  // Always-current ref so handleSaveChangesLayout doesn't need localData in deps
  const localDataRef = useRef(localData);
  localDataRef.current = localData;

  useEffect(() => {
    startTransition(() => setFormReady(true));
  }, []);

  // All hooks must be declared before any early returns
  const handleSaveChangesLayout = useCallback(async () => {
    const current = localDataRef.current;
    try {
      await updateExplorerResults(explorer?.id, current);
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
  }, [explorer?.id, setData, enqueueSnackbar, t]);

  const handleSetData = useCallback((newData) => {
    setLocalData((prev) => ({ ...prev, data: newData }));
  }, []);

  const handleSetLayout = useCallback((newLayout) => {
    setLocalData((prev) => ({ ...prev, layout: newLayout }));
  }, []);

  if (!explorer) return null;
  if (!data) return null;

  const tabs = [
    { label: t("common:info"), value: 0, icon: <InfoOutlined /> },
    { label: t("common:columns"), value: 1, icon: <ViewColumnOutlined /> },
    { label: t("common:parameters"), value: 2, icon: <TuneOutlined /> },
    { label: t("common:results"), value: 3, icon: <AnalyticsOutlined /> },
  ];

  const handleTabChange = (_, newValue) => {
    startTransition(() => setCurrentTab(newValue));
  };

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
          },
        },
      }}
    >
      <DialogTitle
        sx={{ display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}
      >
        <Typography variant="h6" component="div">
          {t("datasets:label.detailsForExplorer", {
            name: explorerComponent.display_name,
          })}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        <IconButton onClick={onClose}>
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
        }}
      >
        {/* Tab bar */}
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          centered
          sx={{ borderBottom: 1, borderColor: "divider", flexShrink: 0 }}
        >
          {tabs.map((tab) => (
            <Tab
              key={tab.value}
              value={tab.value}
              label={tab.label}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>

        {/* Tab content */}
        <Box sx={{ flex: 1, overflow: "hidden", position: "relative" }}>
          {/* Non-results tabs: conditionally rendered, padded */}
          {currentTab === 0 && (
            <Box sx={{ p: 3, height: "100%", overflowY: "auto" }}>
              <TabInfo data={explorer} />
            </Box>
          )}
          {currentTab === 1 && (
            <Box sx={{ p: 3, height: "100%", overflowY: "auto" }}>
              <TabColumns data={explorer.columns} />
            </Box>
          )}
          {currentTab === 2 && (
            <Box sx={{ p: 3, height: "100%", overflowY: "auto" }}>
              <TabParameters data={explorer.parameters} />
            </Box>
          )}

          {/* Results tab: always mounted to preserve state, side-by-side layout */}
          <Box
            sx={{
              display: currentTab === 3 ? "flex" : "none",
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
              >
                {t("common:loading")}
              </CircularProgress>
            )}
            {/* Chart panel */}
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
                    p: 2,
                  }}
                >
                  <TabResults
                    id={explorer.id}
                    data={localData}
                    dataType={dataType}
                    loading={loading}
                  />
                </Box>

                {/* Form sidebar — deferred until after first paint */}
                {dataType === "plotly_json" && (
                  <Box
                    sx={{
                      width: { xs: "100%", xl: "50%" },
                      flexShrink: 0,
                      overflowY: { xs: "visible", xl: "auto" },
                      mt: { xs: 2, xl: 0 },
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
