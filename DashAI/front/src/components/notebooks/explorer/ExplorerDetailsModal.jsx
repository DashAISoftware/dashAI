import React, { useState } from "react";
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
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);

  if (!explorer) return null;
  if (!data) return null;

  const tabs = [
    { label: t("common:info"), value: 0, icon: <InfoOutlined /> },
    { label: t("common:columns"), value: 1, icon: <ViewColumnOutlined /> },
    { label: t("common:parameters"), value: 2, icon: <TuneOutlined /> },
    { label: t("common:results"), value: 3, icon: <AnalyticsOutlined /> },
  ];

  const handleTabChange = (_, newValue) => {
    setCurrentTab(newValue);
  };

  const handleSaveChangesLayout = async () => {
    try {
      await updateExplorerResults(explorer.id, localData);
      setData(localData);
      enqueueSnackbar(
        t("datasets:message.explorerResultsUpdatedSuccessfully"),
        {
          variant: "success",
        },
      );
    } catch (error) {
      console.error("Failed to update explorer results:", error);
      enqueueSnackbar(t("datasets:error.failedToUpdateExplorerResults"), {
        variant: "error",
      });
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      sx={{
        "& .MuiDialog-container": {
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        },
      }}
      slotProps={{
        paper: {
          sx: {
            width: 1400,
            height: "90vh",
            maxWidth: "none",
            m: "auto",
          },
        },
      }}
    >
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
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
      <Divider />
      <DialogContent sx={{ p: 0 }}>
        <Box sx={{ mt: 0 }} elevation={0}>
          <Tabs
            value={currentTab}
            onChange={handleTabChange}
            centered
            sx={{ borderBottom: 1, borderColor: "divider" }}
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

          <Box sx={{ p: 3, height: "100%" }}>
            {currentTab === 0 && <TabInfo data={explorer} />}
            {currentTab === 1 && <TabColumns data={explorer.columns} />}
            {currentTab === 2 && <TabParameters data={explorer.parameters} />}
            <Box
              sx={{
                display: currentTab === 3 ? "block" : "none",
                height: "100%",
              }}
            >
              <TabResults
                id={explorer.id}
                data={localData}
                dataType={dataType}
                loading={loading}
              />
              {dataType === "plotly_json" && (
                <PlotLayoutForm
                  data={localData.data}
                  setData={(newData) => {
                    setLocalData((prevData) => ({
                      ...prevData,
                      data: newData,
                    }));
                  }}
                  layout={localData.layout}
                  setLayout={(newLayout) => {
                    setLocalData((prevData) => ({
                      ...prevData,
                      layout: newLayout,
                    }));
                  }}
                  onSave={handleSaveChangesLayout}
                />
              )}
            </Box>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
