import React from "react";
import PropTypes from "prop-types";
import { Tabs, Tab, Typography, Paper, Box, Button } from "@mui/material";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import CustomLayout from "../../../components/custom/CustomLayout";
import ResultsTabInfo from "./ResultsTabInfo";
import ResultsTabParameters from "./ResultsTabParameters";
import ResultsTabMetrics from "./ResultsTabMetrics";
import ResultsTabHyperparameters from "./ResultsTabHyperparameters";
import { tabsResultsDetails } from "../constants/tabsResultsDetails";
import { checkIfHaveOptimazers } from "../../../utils/schema";
import { useTranslation } from "react-i18next";

function ResultsDetailsLayout({
  runData,
  currentTab,
  handleTabChange,
  handleCloseCustomLayout,
  handleRun,
}) {
  const { t } = useTranslation(["common"]);
  const optimizables = checkIfHaveOptimazers(runData.parameters);
  const updatedTabs = tabsResultsDetails.map((tab) => ({
    ...tab,
    disabled: tab.value === 3 ? !optimizables : tab.disabled,
  }));
  return (
    <CustomLayout>
      <Button
        startIcon={<ArrowBackIosNewIcon />}
        onClick={handleCloseCustomLayout}
      >
        {t("common:close")}
      </Button>

      <Paper sx={{ mt: 2 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          {updatedTabs.map((tab) => (
            <Tab
              key={tab.value}
              value={tab.value}
              label={tab.label}
              disabled={tab.disabled}
            />
          ))}
        </Tabs>
        <Box sx={{ p: 3, height: "100%" }}>
          {currentTab === 0 && (
            <ResultsTabInfo runData={runData} handleRun={handleRun} />
          )}
          {/* {currentTab === 1 && <ResultsTabParameters runData={runData} />}
          {currentTab === 2 && <ResultsTabMetrics runData={runData} />} */}
          {currentTab === 3 && <ResultsTabHyperparameters runData={runData} />}
          {currentTab === 4 && <Typography>{t("common:todo")}</Typography>}
        </Box>
      </Paper>
    </CustomLayout>
  );
}

ResultsDetailsLayout.propTypes = {
  runData: PropTypes.object,
  currentTab: PropTypes.number,
  setUpdateDataFlag: PropTypes.func,
  handleTabChange: PropTypes.func,
  handleCloseCustomLayout: PropTypes.func,
};

export default ResultsDetailsLayout;
