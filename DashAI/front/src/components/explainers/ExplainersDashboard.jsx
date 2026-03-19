import React, { useState } from "react";
import PropTypes from "prop-types";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import { Button, Grid, Paper, Tab, Tabs, Typography } from "@mui/material";
import CustomLayout from "../custom/CustomLayout";
import NewGlobalExplainerModal from "./NewGlobalExplainerModal";
import NewLocalExplainerModal from "./NewLocalExplainerModal";
import ExplainersGrid from "./ExplainersGrid";
import TimestampWrapper from "../shared/TimestampWrapper";
import { TIMESTAMP_KEYS } from "../../constants/timestamp";
import { useTranslation } from "react-i18next";

function ExplainersTable({ runId, scope, title, handleNewExplainer, description }) {
  const { t } = useTranslation(["explainers"]);
  return (
    <Grid size={{ xs: 12 }}>
      <Paper sx={{ py: 2, px: 2 }}>
        <Grid
          container
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: 4 }}
        >
          <Typography variant="h4" component="h2">
            {title}
          </Typography>
          <Grid>
            <TimestampWrapper
              eventName={
                TIMESTAMP_KEYS.explainer[
                  `configure${scope.charAt(0).toUpperCase() + scope.slice(1)}`
                ]
              }
            >
              <Button
                variant="contained"
                onClick={handleNewExplainer}
                endIcon={<AddIcon />}
              >
                {t("explainers:button.addExplainer")}
              </Button>
            </TimestampWrapper>
          </Grid>
        </Grid>
        <Typography variant="h6" component="h2">
          {description}
        </Typography>
        <ExplainersGrid runId={runId} scope={scope} />
      </Paper>
    </Grid>
  );
}
ExplainersTable.propTypes = {
  runId: PropTypes.string.isRequired,
  scope: PropTypes.string.isRequired,
  handleNewExplainer: PropTypes.func.isRequired,
  description: PropTypes.string.isRequired,
};

export default function ExplainersDashboard() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { modelName } = location.state ?? "";
  const { taskName } = location.state ?? "";
  const [showNewGlobalExplainerModal, setShowNewGlobalExplainerModal] =
    useState(false);
  const [showNewLocalExplainerModal, setShowNewLocalExplainerModal] =
    useState(false);
  const { t } = useTranslation(["explainers"]);

  const handleNewGlobalExplainerModal = () => {
    setShowNewGlobalExplainerModal(true);
  };

  const handleNewLocalExplainerModal = () => {
    setShowNewLocalExplainerModal(true);
  };

  const [currentTab, setCurrentTab] = useState(0);

  const tabs = [
    {
      label: t("explainers:label.globalExplanations"),
      value: 0,
      disabled: false,
    },
    {
      label: t("explainers:label.localExplanations"),
      value: 1,
      disabled: false,
    },
  ];

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  const explainerConfig = {
    runId: id,
    taskName: taskName,
  };

  return (
    <CustomLayout>
      <NewGlobalExplainerModal
        open={showNewGlobalExplainerModal}
        setOpen={setShowNewGlobalExplainerModal}
        explainerConfig={explainerConfig}
      />
      <NewLocalExplainerModal
        open={showNewLocalExplainerModal}
        setOpen={setShowNewLocalExplainerModal}
        explainerConfig={explainerConfig}
      />
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        {t("explainers:label.explainersDashboardTitle", {
          modelName: modelName,
        })}
      </Typography>
      <Typography variant="h6" component="h1" sx={{ mb: 3 }}>
        {t("explainers:label.explainersDashboardDescription")}
      </Typography>
      <TimestampWrapper eventName={TIMESTAMP_KEYS.explainer.leavingDashboard}>
        <Button
          startIcon={<ArrowBackIosNewIcon />}
          onClick={() => {
            navigate(`/app/explainers`);
          }}
        >
          {t("explainers:button.backToExplainers")}
        </Button>
      </TimestampWrapper>

      <Tabs value={currentTab} onChange={handleTabChange}>
        {tabs.map((tab) => (
          <Tab
            key={tab.value}
            value={tab.value}
            label={tab.label}
            disabled={tab.disabled}
          />
        ))}
      </Tabs>
      <Grid container spacing={2}>
        {currentTab === 0 && (
          <ExplainersTable
            runId={id}
            scope={"global"}
            title={t("explainers:label.globalExplanations")}
            handleNewExplainer={handleNewGlobalExplainerModal}
            description={t("explainers:label.globalExplanationsDescription")}
          />
        )}
        {currentTab === 1 && (
          <ExplainersTable
            runId={id}
            scope={"local"}
            title={t("explainers:label.localExplanations")}
            handleNewExplainer={handleNewLocalExplainerModal}
            description={t("explainers:label.localExplanationsDescription")}
          />
        )}
      </Grid>
    </CustomLayout>
  );
}
