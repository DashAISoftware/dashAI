import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Grid,
  Paper,
  Typography,
  Box,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Chip,
} from "@mui/material";
import {
  Edit as EditIcon,
  Settings as SettingsIcon,
  Close as CloseIcon,
} from "@mui/icons-material";

import FormSchemaDialog from "../../../shared/FormSchemaDialog";
import FormSchemaWithSelectedModel from "../../../shared/FormSchemaWithSelectedModel";
import { getComponents } from "../../../../api/component";
import { useTranslation } from "react-i18next";

// Metrics Section Component
const MetricsSection = ({ title, metrics }) => (
  <Paper elevation={2} sx={{ p: 2, height: "100%" }}>
    <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
      {title}
    </Typography>
    <Divider sx={{ mb: 2 }} />
    {metrics &&
      Object.entries(metrics).map(([key, value]) => (
        <Box
          key={key}
          sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
        >
          <Typography variant="body2" color="text.secondary">
            {key}:
          </Typography>
          <Typography variant="body2" fontWeight="medium">
            {typeof value === "number" ? value.toFixed(4) : value}
          </Typography>
        </Box>
      ))}
  </Paper>
);

export default function RunInfoModal({
  experiment,
  run,
  setRun,
  open,
  onClose,
  onEditParameters,
  onOptimize,
}) {
  // Initialize all hooks FIRST (before any conditional returns)
  const [localRun, setLocalRun] = useState(() => 
    run ? structuredClone(run) : null
  );
  const [metrics, setMetrics] = useState([]);
  const [optimizers, setOptimizers] = useState([]);
  const { t } = useTranslation(["experiments", "common"]);

  useEffect(() => {
    if (!experiment) return; // Guard inside useEffect
    
    const fetchMetricsAndOptimizers = async () => {
      try {
        const components = await getComponents({
          selectTypes: ["Metric", "Optimizer"],
          relatedComponent: experiment.task_name,
        });
        const fetchedMetrics = components.filter((c) => c.type === "Metric");
        const fetchedOptimizers = components.filter(
          (c) => c.type === "Optimizer",
        );
        setMetrics(fetchedMetrics);
        setOptimizers(fetchedOptimizers);
      } catch (error) {
        console.error("Error fetching metrics and optimizers:", error);
      }
    };
    fetchMetricsAndOptimizers();
  }, [experiment?.task_name]); // Update dependency array

  const getStatusColor = (status) => {
    switch (status) {
      case 3: // Finished
        return "success";
      case 2: // Started
      case 1: // Delivered
        return "info";
      case 4: // Error
        return "error";
      default:
        return "default";
    }
  };

  // Guard clause AFTER all hooks
  if (!run || !experiment) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xl" fullWidth>
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box>
          <Typography variant="h5" component="span" fontWeight="bold">
            {run.name}
          </Typography>
          <Chip
            label={run.status}
            color={getStatusColor(run.status)}
            size="small"
            sx={{ ml: 2 }}
          />
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {/* Run Details Section */}
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 6, md: 3 }}>
              <Typography variant="caption" color="text.secondary">
                {t("experiments:label.modelName")}
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {run.model_name}
              </Typography>
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <Typography variant="caption" color="text.secondary">
                {t("experiments:label.startTime")}
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {new Date(run.start_time).toLocaleString()}
              </Typography>
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <Typography variant="caption" color="text.secondary">
                {t("experiments:label.endTime")}
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {new Date(run.end_time).toLocaleString()}
              </Typography>
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <Typography variant="caption" color="text.secondary">
                {t("experiments:label.duration")}
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {(
                  (new Date(run.end_time) - new Date(run.start_time)) /
                  1000
                ).toFixed(2)}
                s
              </Typography>
            </Grid>
          </Grid>
        </Paper>

        {/* Metrics Section */}
        <Typography variant="h6" gutterBottom>
          {t("experiments:metrics.metrics")}
        </Typography>
        <Box
          sx={{
            display: "flex",
            gap: 2,
            mb: 3,
            width: "100%",
            flexWrap: "wrap",
          }}
        >
          <Box sx={{ flex: 1, minWidth: 300 }}>
            <MetricsSection
              title={t("experiments:metrics.trainingMetrics")}
              metrics={run.train_metrics}
            />
          </Box>

          <Box sx={{ flex: 1, minWidth: 300 }}>
            <MetricsSection
              title={t("experiments:metrics.validationMetrics")}
              metrics={run.validation_metrics}
            />
          </Box>

          <Box sx={{ flex: 1, minWidth: 300 }}>
            <MetricsSection
              title={t("experiments:metrics.testMetrics")}
              metrics={run.test_metrics}
            />
          </Box>
        </Box>

        {/* Parameter modification */}
        <Typography variant="h6" gutterBottom>
          {t("experiments:label.parameterModification")}
        </Typography>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, md: 4 }}>
              <Button
                variant="contained"
                startIcon={<EditIcon />}
                fullWidth
                onClick={onEditParameters}
                size="large"
              >
                {t("experiments:button.editParameters")}
              </Button>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <FormControl fullWidth>
                <InputLabel>
                  {t("experiments:label.metricToOptimize")}
                </InputLabel>
                <Select
                  value={localRun.goal_metric || ""}
                  label={t("experiments:label.metricToOptimize")}
                  onChange={(e) =>
                    setLocalRun({
                      ...localRun,
                      goal_metric: e.target.value,
                    })
                  }
                >
                  {metrics.map((metric) => (
                    <MenuItem key={metric.name} value={metric.name}>
                      {metric.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Box sx={{ display: "flex", gap: 1 }}>
                <FormControl fullWidth>
                  <InputLabel>{t("experiments:label.optimizer")}</InputLabel>
                  <Select
                    value={localRun.optimizer_name || ""}
                    label={t("experiments:label.optimizer")}
                    onChange={(e) =>
                      setLocalRun({
                        ...localRun,
                        optimizer_name: e.target.value,
                      })
                    }
                  >
                    {optimizers.map((optimizer) => (
                      <MenuItem key={optimizer.name} value={optimizer.name}>
                        {optimizer.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <IconButton
                  color="primary"
                  onClick={() =>
                    onOptimize && onOptimize(localRun.optimizer_name)
                  }
                >
                  <SettingsIcon />
                </IconButton>
              </Box>
            </Grid>
          </Grid>

          {/* Current Optimizer Info */}
          {run.optimizer_parameters && (
            <Box
              sx={{
                mt: 2,
                p: 2,
                bgcolor: "background.default",
                borderRadius: 1,
              }}
            >
              <Typography variant="subtitle2" gutterBottom>
                {t("label.currentOptimizerSettings", {
                  optimizer: run.optimizer_name,
                })}
              </Typography>
              <Grid container spacing={1}>
                {Object.entries(run.optimizer_parameters).map(
                  ([key, value]) => (
                    <Grid size={{ xs: 6, md: 4 }} key={key}>
                      <Typography variant="caption" color="text.secondary">
                        {key}:
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {String(value)}
                      </Typography>
                    </Grid>
                  ),
                )}
              </Grid>
            </Box>
          )}
        </Paper>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} variant="outlined">
          {t("common:close")}
        </Button>
        <Button
          onClick={() =>
            onOptimize &&
            onOptimize(localRun.optimizer_name, localRun.goal_metric)
          }
          variant="contained"
          disabled={!localRun.goal_metric}
        >
          {t("common:saveAndRun")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
