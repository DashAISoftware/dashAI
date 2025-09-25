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

const tabs = [
  { label: "Info", value: 0, icon: <InfoOutlined /> },
  { label: "Columns", value: 1, icon: <ViewColumnOutlined /> },
  { label: "Parameters", value: 2, icon: <TuneOutlined /> },
  { label: "Results", value: 3, icon: <AnalyticsOutlined /> },
];

const defaultTab = tabs.find((tab) => tab.label === "Results").value;

const MemoizedResultTab = React.memo(
  TabResults,
  (prev, next) => prev.id == next.id,
);

export default function ExplorerDetailsModal({
  open = false,
  onClose = () => {},
  explorer,
}) {
  if (!explorer) return null;
  const [currentTab, setCurrentTab] = useState(defaultTab);

  const handleTabChange = (_, newValue) => {
    setCurrentTab(newValue);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: 1400,
          height: 700,
          maxWidth: "none",
          m: "auto",
        },
      }}
      sx={{
        "& .MuiDialog-container": {
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
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
              <MemoizedResultTab id={explorer.id} />
            </Box>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
