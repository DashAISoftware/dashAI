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

const tabs = [
  { label: "Info", value: 0, icon: <InfoOutlined /> },
  { label: "Columns", value: 1, icon: <ViewColumnOutlined /> },
  { label: "Parameters", value: 2, icon: <TuneOutlined /> },
  { label: "Results", value: 3, icon: <AnalyticsOutlined /> },
];

const defaultTab = tabs.find((tab) => tab.label === "Results").value;

export default function ExplorerDetailsModal({
  open = false,
  onClose = () => {},
  explorer,
  data,
  setData,
  dataType,
  loading,
}) {
  if (!explorer) return null;
  if (!data) return null;
  const [currentTab, setCurrentTab] = useState(defaultTab);
  const [localData, setLocalData] = useState(structuredClone(data));
  const { enqueueSnackbar } = useSnackbar();

  const handleTabChange = (_, newValue) => {
    setCurrentTab(newValue);
  };

  const handleSaveChangesLayout = async () => {
    try {
      await updateExplorerResults(explorer.id, localData);
      setData(localData);
      enqueueSnackbar("Explorer results updated successfully", {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update explorer results:", error);
      enqueueSnackbar("Failed to update explorer results", {
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
        <Typography variant="h6">
          Details for Explorer: {explorer.name}
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
