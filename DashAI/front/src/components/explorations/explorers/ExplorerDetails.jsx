import React, { useState } from "react";
import PropTypes from "prop-types";

import { Tabs, Tab, Button, Paper, Box } from "@mui/material";

import {
  ArrowBackIosNew as BackIcon,
  InfoOutlined,
  ViewColumnOutlined,
  TuneOutlined,
  AnalyticsOutlined,
} from "@mui/icons-material";

import { useExplorationsContext } from "../context";
import CustomLayout from "../../custom/CustomLayout";
import { TabColumns, TabInfo, TabParameters, TabResults } from "./DetailTabs";

const tabs = [
  {
    label: "Info",
    value: 0,
    icon: <InfoOutlined />,
  },
  {
    label: "Columns",
    value: 1,
    icon: <ViewColumnOutlined />,
  },
  {
    label: "Parameters",
    value: 2,
    icon: <TuneOutlined />,
  },
  {
    label: "Results",
    value: 3,
    icon: <AnalyticsOutlined />,
  },
];
const defaultTab = tabs.find((tab) => tab.label === "Results").value;

/**
 * Component to display the details of an explorer
 * @param {Object} props
 * @param {Function} props.handleClose - Function to close the dialog
 * @param {Boolean} props.updateFlag - Flag to update the data
 * @param {Function} props.setUpdateFlag - Function to set the update flag
 */
function ExplorerDetails({
  handleClose = () => {},
  updateFlag = false,
  setUpdateFlag = () => {},
}) {
  const { explorerData } = useExplorationsContext();

  const [currentTab, setCurrentTab] = useState(defaultTab);

  const handleTabChange = (_, newValue) => {
    setCurrentTab(newValue);
  };

  return (
    <CustomLayout>
      <Button startIcon={<BackIcon />} onClick={handleClose}>
        Close details
      </Button>

      <Paper sx={{ mt: 2 }} elevation={0}>
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
          {currentTab === 0 && <TabInfo data={explorerData} />}
          {currentTab === 1 && <TabColumns data={explorerData.columns} />}
          {currentTab === 2 && <TabParameters data={explorerData.parameters} />}
          {currentTab === 3 && (
            <TabResults
              id={explorerData.id}
              updateFlag={updateFlag}
              setUpdateFlag={setUpdateFlag}
            />
          )}
        </Box>
      </Paper>
    </CustomLayout>
  );
}

ExplorerDetails.propTypes = {
  handleClose: PropTypes.func,
  updateFlag: PropTypes.bool,
  setUpdateFlag: PropTypes.func,
};

export default ExplorerDetails;
