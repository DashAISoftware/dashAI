import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import {
  Divider,
  Grid,
  Paper,
  Typography,
  Box,
  Chip,
  Button,
  Alert,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  Edit as EditIcon,
  Settings as SettingsIcon,
} from "@mui/icons-material";
import MetricsCard from "./MetricsCard";
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
} from "@mui/material";
import { getModelSessionById } from "../../../api/modelSession";
import { getComponents } from "../../../api/component";
import { checkIfHaveOptimazers } from "../../../utils/schema";
import FormSchemaDialog from "../../../components/shared/FormSchemaDialog";
import FormSchemaWithSelectedModel from "../../../components/shared/FormSchemaWithSelectedModel";
import { updateRunParameters } from "../../../api/run";
import { useSnackbar } from "notistack";
import OptimizationTableSelectOptimizer from "../../../components/models/modelSession/OptimizationTableSelectOptimizer";
import { getColorByStatus } from "../../../utils";
import LiveMetricsChart from "./LiveMetricsChart";
import { useTranslation } from "react-i18next";
import { getRunStatus } from "../../../utils/runStatus";

/**
 * Component that displays general information associated with a run.
 * @param {object} runData object that contains all the necessary info of the run
 */
function ResultsTabInfo({ runData, handleRun }) {
  const theme = useTheme();
  const [localRun, setLocalRun] = React.useState(structuredClone(runData));
  const [openParametersDialog, setOpenParametersDialog] = useState(false);
  const [openOptimizerParametersDialog, setOpenOptimizerParametersDialog] =
    useState(false);
  const [metrics, setMetrics] = useState([]);
  const [optimizers, setOptimizers] = useState([]);
  const experiment = useRef(null);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["models", "common"]);

  useEffect(() => {
    const fetchMetricsAndOptimizers = async () => {
      try {
        const experiment = await getModelSessionById(runData.model_session_id);
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

    const fetchExperiment = async () => {
      try {
        const exp = await getModelSessionById(runData.model_session_id);
        experiment.current = exp;
      } catch (error) {
        console.error("Error fetching experiment:", error);
      }
    };

    fetchExperiment();
    fetchMetricsAndOptimizers();
  }, []);

  const onEditParameters = () => {
    setOpenParametersDialog(true);
  };

  useEffect(() => {
    setLocalRun(structuredClone(runData));
  }, [runData]);

  const optimizables = checkIfHaveOptimazers(localRun.parameters);

  const updateParameters = async () => {
    await updateRunParameters(
      localRun.id,
      localRun.parameters,
      localRun.optimizer_name,
      localRun.optimizer_parameters,
      localRun.goal_metric,
    );
    enqueueSnackbar(t("models:message.parametersUpdatedSuccessfully"), {
      variant: "success",
    });
    handleRun(localRun);
  };

  const isLocked = runData.status === 1 || runData.status === 2; // Delivered or Started

  return (
    <Grid container direction="column">
      {/* Run Details Section */}
      {(runData.model_name || runData.start_time || runData.end_time) && (
        <>
          <Divider sx={{ mt: 6, mb: 6 }} />
          <Paper variant="outlined" sx={{ p: 4, mb: 6 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                mb: 4,
                justifyContent: "space-between",
              }}
            >
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                {t("models:label.runDetails")}
              </Typography>
              {/* Status Badge */}
              {runData.status && (
                <Box>
                  <Chip
                    label={getRunStatus(runData.status, t)}
                    sx={{
                      backgroundColor: getColorByStatus(runData.status, theme),
                    }}
                    size="medium"
                  />
                </Box>
              )}
            </Box>
            <Grid container spacing={4}>
              {runData.model_name && (
                <Grid size={{ xs: 6, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">
                    {t("common:model")}
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {runData.model_name}
                  </Typography>
                </Grid>
              )}
              {runData.start_time && (
                <Grid size={{ xs: 6, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">
                    {t("common:startTime")}
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {new Date(runData.start_time).toLocaleString()}
                  </Typography>
                </Grid>
              )}
              {runData.end_time && (
                <Grid size={{ xs: 6, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">
                    {t("common:endTime")}
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {new Date(runData.end_time).toLocaleString()}
                  </Typography>
                </Grid>
              )}
              {runData.start_time &&
                runData.status !== 4 && ( // Not Failed
                  <Grid size={{ xs: 6, md: 3 }}>
                    <Typography variant="caption" color="text.secondary">
                      {t("common:duration")}
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {runData.status === 3 // Finished
                        ? (
                            (new Date(runData.end_time) -
                              new Date(runData.start_time)) /
                            1000
                          ).toFixed(2)
                        : (
                            (new Date() - new Date(runData.start_time)) /
                            1000
                          ).toFixed(2)}{" "}
                      {t("common:seconds")}
                    </Typography>
                  </Grid>
                )}
            </Grid>
          </Paper>
        </>
      )}

      {/* Live Metrics Section */}
      <Divider sx={{ mt: 6, mb: 4 }} />

      <Typography variant="h6" gutterBottom>
        {t("models:label.liveMetrics")}
      </Typography>

      <Paper variant="outlined" sx={{ p: 4 }}>
        <LiveMetricsChart run={runData} />
      </Paper>

      {/* Metrics Section */}
      {(runData.train_metrics ||
        runData.validation_metrics ||
        runData.test_metrics) && (
        <>
          <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
            {t("common:metrics")}
          </Typography>
          <Box
            sx={{
              display: "flex",
              gap: 4,
              mb: 6,
              width: "100%",
              flexWrap: "wrap",
            }}
          >
            {runData.train_metrics && (
              <Box sx={{ flex: 1, minWidth: 300 }}>
                <MetricsCard
                  title={t("models:label.trainingMetrics")}
                  metrics={runData.train_metrics}
                />
              </Box>
            )}

            {runData.validation_metrics && (
              <Box sx={{ flex: 1, minWidth: 300 }}>
                <MetricsCard
                  title={t("models:label.validationMetrics")}
                  metrics={runData.validation_metrics}
                />
              </Box>
            )}

            {runData.test_metrics && (
              <Box sx={{ flex: 1, minWidth: 300 }}>
                <MetricsCard
                  title={t("models:label.testMetrics")}
                  metrics={runData.test_metrics}
                />
              </Box>
            )}
          </Box>
        </>
      )}

      <Divider sx={{ mt: 6, mb: 4 }} />

      {/* Run edition */}
      {isLocked && (
        <Alert severity="info">
          {t("models:label.runInProgressCannotEdit")}
        </Alert>
      )}
      {!isLocked && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
            {t("models:label.editRunParameters")}
          </Typography>
          {(localRun.goal_metric === null || localRun.goal_metric === "") &&
          optimizables ? (
            <Alert severity="warning">
              {t("models:label.pleaseSelectMetricToOptimize")}
            </Alert>
          ) : null}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            {/* Edit Parameters Button */}
            <Box
              sx={{
                display: "flex",
                gap: 4,
                alignItems: "center",
              }}
            >
              <Button
                variant="contained"
                startIcon={<EditIcon />}
                onClick={onEditParameters}
              >
                {t("models:button.modifyParameters")}
              </Button>
            </Box>
            {/* Optimization Section */}
            {optimizables && (
              <Box
                sx={{
                  display: "flex",
                  gap: 4,
                }}
              >
                <Box>
                  <FormControl sx={{ width: "300px" }}>
                    <InputLabel>
                      {t("models:label.metricToOptimize")}
                    </InputLabel>
                    <Select
                      value={localRun.goal_metric || ""}
                      label={t("models:label.metricToOptimize")}
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
                </Box>
                <Box sx={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <Box sx={{ width: "300px" }}>
                    <OptimizationTableSelectOptimizer
                      taskName={experiment.current?.task_name}
                      optimizerName={localRun.optimizer_name}
                      handleSelectedOptimizer={(
                        optimizerName,
                        optimizerParams,
                      ) => {
                        setLocalRun({
                          ...localRun,
                          optimizer_name: optimizerName,
                          optimizer_parameters: optimizerParams,
                        });
                      }}
                    />
                  </Box>

                  <IconButton
                    color="primary"
                    onClick={() => setOpenOptimizerParametersDialog(true)}
                    disabled={!localRun.optimizer_name}
                  >
                    <SettingsIcon />
                  </IconButton>
                </Box>
              </Box>
            )}
          </Box>
          {/* Parameters Form Dialog */}
          <FormSchemaDialog
            modelToConfigure={localRun.model_name}
            open={openParametersDialog}
            setOpen={setOpenParametersDialog}
            onFormSubmit={() => {}}
          >
            <FormSchemaWithSelectedModel
              onFormSubmit={(values) => {
                setLocalRun({
                  ...localRun,
                  parameters: values,
                });
                setOpenParametersDialog(false);
              }}
              modelToConfigure={localRun.model_name}
              initialValues={localRun.parameters}
              onCancel={() => setOpenParametersDialog(false)}
            />
          </FormSchemaDialog>

          {/* Optimizer Configuration Dialog */}
          <FormSchemaDialog
            modelToConfigure={localRun.optimizer_name}
            open={openOptimizerParametersDialog}
            setOpen={setOpenOptimizerParametersDialog}
            onFormSubmit={() => {}}
          >
            <FormSchemaWithSelectedModel
              onFormSubmit={(values) => {
                setLocalRun({
                  ...localRun,
                  optimizer_parameters: values,
                });
                setOpenOptimizerParametersDialog(false);
              }}
              modelToConfigure={localRun.optimizer_name}
              initialValues={localRun.optimizer_parameters}
              onCancel={() => setOpenOptimizerParametersDialog(false)}
            />
          </FormSchemaDialog>

          {/* Save and run button */}
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 4 }}>
            <Button
              variant="outlined"
              sx={{ mr: 4 }}
              onClick={() => {
                setLocalRun(structuredClone(runData));
              }}
              disabled={JSON.stringify(localRun) === JSON.stringify(runData)}
            >
              {t("common:cancel")}
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={updateParameters}
              disabled={
                optimizables
                  ? localRun.goal_metric === null || localRun.goal_metric === ""
                  : false
              }
            >
              {JSON.stringify(localRun) === JSON.stringify(runData)
                ? t("models:button.runModel")
                : t("models:button.saveAndRunModel")}
            </Button>
          </Box>
        </Box>
      )}
    </Grid>
  );
}

ResultsTabInfo.propTypes = {
  runData: PropTypes.shape({
    status: PropTypes.number,
    model_name: PropTypes.string,
    start_time: PropTypes.string,
    end_time: PropTypes.string,
    train_metrics: PropTypes.object,
    validation_metrics: PropTypes.object,
    test_metrics: PropTypes.object,
    optimizer_name: PropTypes.string,
    optimizer_parameters: PropTypes.object,
  }).isRequired,
};

export default ResultsTabInfo;
