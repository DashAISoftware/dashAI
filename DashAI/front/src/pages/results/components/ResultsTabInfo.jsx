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
import OptimizationTableSelectOptimizer from "../../../components/experiments/OptimizationTableSelectOptimizer";
import { getColorByStatus } from "../../../utils";
import LiveMetricsChart from "./LiveMetricsChart";

/**
 * Component that displays general information associated with a run.
 * @param {object} runData object that contains all the necessary info of the run
 */
function ResultsTabInfo({ runData, handleRun }) {
  const [localRun, setLocalRun] = React.useState(structuredClone(runData));
  const [openParametersDialog, setOpenParametersDialog] = useState(false);
  const [openOptimizerParametersDialog, setOpenOptimizerParametersDialog] =
    useState(false);
  const [metrics, setMetrics] = useState([]);
  const [optimizers, setOptimizers] = useState([]);
  const experiment = useRef(null);
  const { enqueueSnackbar } = useSnackbar();

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
    enqueueSnackbar("Parameters updated successfully", { variant: "success" });
    handleRun(localRun);
  };

  const isLocked =
    runData.status === "Started" || runData.status === "Delivered";

  return (
    <Grid container direction="column">
      {/* Run Details Section */}
      {(runData.model_name || runData.start_time || runData.end_time) && (
        <>
          <Divider sx={{ mt: 3, mb: 3 }} />
          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                mb: 2,
                justifyContent: "space-between",
              }}
            >
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Run Details
              </Typography>
              {/* Status Badge */}
              {runData.status && (
                <Box>
                  <Chip
                    label={runData.status}
                    sx={{ backgroundColor: getColorByStatus(runData.status) }}
                    size="medium"
                  />
                </Box>
              )}
            </Box>
            <Grid container spacing={2}>
              {runData.model_name && (
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Model
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {runData.model_name}
                  </Typography>
                </Grid>
              )}
              {runData.start_time && (
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Start Time
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {new Date(runData.start_time).toLocaleString()}
                  </Typography>
                </Grid>
              )}
              {runData.end_time && (
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    End Time
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {new Date(runData.end_time).toLocaleString()}
                  </Typography>
                </Grid>
              )}
              {runData.start_time && runData.status !== "Error" && (
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Duration
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {runData.status === "Finished"
                      ? (
                          (new Date(runData.end_time) -
                            new Date(runData.start_time)) /
                          1000
                        ).toFixed(2)
                      : (
                          (new Date() - new Date(runData.start_time)) /
                          1000
                        ).toFixed(2)}
                    s
                  </Typography>
                </Grid>
              )}
            </Grid>
          </Paper>
        </>
      )}

      {/* Live Metrics Section */}
      <Divider sx={{ mt: 3, mb: 2 }} />

      <Typography variant="h6" gutterBottom>
        Live Metrics
      </Typography>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <LiveMetricsChart run={runData} />
      </Paper>

      {/* Metrics Section */}
      {(runData.train_metrics ||
        runData.validation_metrics ||
        runData.test_metrics) && (
        <>
          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Metrics
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
            {runData.train_metrics && (
              <Box sx={{ flex: 1, minWidth: 300 }}>
                <MetricsCard
                  title="Training Metrics"
                  metrics={runData.train_metrics}
                />
              </Box>
            )}

            {runData.validation_metrics && (
              <Box sx={{ flex: 1, minWidth: 300 }}>
                <MetricsCard
                  title="Validation Metrics"
                  metrics={runData.validation_metrics}
                />
              </Box>
            )}

            {runData.test_metrics && (
              <Box sx={{ flex: 1, minWidth: 300 }}>
                <MetricsCard
                  title="Test Metrics"
                  metrics={runData.test_metrics}
                />
              </Box>
            )}
          </Box>
        </>
      )}

      <Divider sx={{ mt: 3, mb: 2 }} />

      {/* Run edition */}
      {isLocked && (
        <Alert severity="info">
          Run is currently in progress and cannot be edited.
        </Alert>
      )}
      {!isLocked && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Edit parameters and re-run the model
          </Typography>
          {(localRun.goal_metric === null || localRun.goal_metric === "") &&
          optimizables ? (
            <Alert severity="warning">
              Please select a metric to optimize.
            </Alert>
          ) : null}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            {/* Edit Parameters Button */}
            <Box
              sx={{
                display: "flex",
                gap: 2,
                alignItems: "center",
              }}
            >
              <Button
                variant="contained"
                startIcon={<EditIcon />}
                onClick={onEditParameters}
              >
                Modify Parameters
              </Button>
            </Box>
            {/* Optimization Section */}
            {optimizables && (
              <Box
                sx={{
                  display: "flex",
                  gap: 2,
                }}
              >
                <Box>
                  <FormControl sx={{ width: "300px" }}>
                    <InputLabel>Metric to Optimize</InputLabel>
                    <Select
                      value={localRun.goal_metric || ""}
                      label="Metric to Optimize"
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
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
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
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
            <Button
              variant="outlined"
              sx={{ mr: 2 }}
              onClick={() => {
                setLocalRun(structuredClone(runData));
              }}
              disabled={JSON.stringify(localRun) === JSON.stringify(runData)}
            >
              Cancel
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
                ? "Run Model"
                : "Save and Run Model"}
            </Button>
          </Box>
        </Box>
      )}
    </Grid>
  );
}

ResultsTabInfo.propTypes = {
  runData: PropTypes.shape({
    status: PropTypes.string,
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
