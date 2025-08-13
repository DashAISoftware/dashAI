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
  ArrowBackIosNew as BackIcon,
  InfoOutlined,
  ViewColumnOutlined,
  TuneOutlined,
  AnalyticsOutlined,
  Close as CloseIcon,
} from "@mui/icons-material";

import {
  TabColumns,
  TabResults,
  TabInfo,
  TabParameters,
} from "./ExplorerDetailTabs";

const tabs = [
  { label: "Info", value: 0, icon: <InfoOutlined /> },
  { label: "Columns", value: 1, icon: <ViewColumnOutlined /> },
  { label: "Parameters", value: 2, icon: <TuneOutlined /> },
  { label: "Results", value: 3, icon: <AnalyticsOutlined /> },
];

const defaultTab = tabs.find((tab) => tab.label === "Results").value;

const MemoizedResultTab = React.memo(TabResults, (prevProps, nextProps) => {
  return (
    prevProps.id === nextProps.id &&
    prevProps.updateFlag === nextProps.updateFlag
  );
});

export default function ExplorerDetailsModal({
  open = false,
  onClose = () => {},
  explorer,
  updateFlag = false,
  setUpdateFlag = () => {},
}) {
  const [currentTab, setCurrentTab] = useState(defaultTab);

  const handleTabChange = (_, newValue) => {
    setCurrentTab(newValue);
  };

  if (!explorer) return null;

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xl">
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
            {currentTab === 3 && (
              <MemoizedResultTab id={explorer.id} updateFlag={updateFlag} />
            )}
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
