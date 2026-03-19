import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  DialogContent,
  Typography,
  TextField,
  MenuItem,
  Grid,
  IconButton,
  FormControlLabel,
  Checkbox,
} from "@mui/material";
import SettingsIcon from "@mui/icons-material/Settings";
import useSchema from "../../../hooks/useSchema";
import ParamsSettings from "../ParamsSettings";
import { getComponents as getComponentsRequest } from "../../../api/component";
import { validateColumns as validateColumnsRequest } from "../../../api/modelSession";
import { useSnackbar } from "notistack";
import { getDatasetInfo as getDatasetInfoRequest } from "../../../api/datasets";
import { parseRangeToIndex } from "../../../utils/parseRange";
import { validateNode } from "../../../api/pipeline";

const Train = ({ open, onClose, onSave, savedConfig, prevNodes }) => {
  const [inputColumns, setInputColumns] = useState(
    savedConfig?.input_columns || "",
  );
  const [outputColumns, setOutputColumns] = useState(
    savedConfig?.output_columns || "",
  );
  const [splits, setSplits] = useState(
    savedConfig?.splits || {
      train: 60,
      validation: 20,
      test: 20,
      shuffle: true,
      stratify: false,
      splitType: "random",
    },
  );
  const [task, setTask] = useState(savedConfig?.task || "");
  const [model, setModel] = useState(savedConfig?.model || "");
  const [metrics, setMetrics] = useState(savedConfig?.metrics || []);
  const [openSettings, setOpenSettings] = useState(false);
  const [modelParams, setModelParams] = useState(savedConfig?.parameters || {});
  const initializedForModelRef = useRef(null);
  const [availableTasks, setAvailableTasks] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [availableMetrics, setAvailableMetrics] = useState([]);
  const { enqueueSnackbar } = useSnackbar();
  const datasetNode = prevNodes?.find((node) => node?.file_path && node?.id);
  const datasetId = datasetNode?.id ?? null;
  const [validTasks, setValidTasks] = useState([]);
  const [datasetInfo, setDatasetInfo] = useState({});
  const [infoLoading, setInfoLoading] = useState(true);
  const [inputError, setInputError] = useState(false);
  const [outputError, setOutputError] = useState(false);
  const [inputErrorMessage, setInputErrorMessage] = useState("");
  const [outputErrorMessage, setOutputErrorMessage] = useState("");
  const [validationStatus, setValidationStatus] = useState("");

  useEffect(() => {
    const fetchComponents = async () => {
      try {
        const tasks = await getComponentsRequest({ selectTypes: ["Task"] });
        const models = await getComponentsRequest({
          selectTypes: ["Model"],
          relatedComponent: task,
        });
        const metrics = await getComponentsRequest({
          selectTypes: ["Metric"],
          relatedComponent: task,
        });

        setAvailableTasks(tasks);
        setAvailableModels(models);
        setAvailableMetrics(metrics);
      } catch (error) {
        console.error("Error fetching components:", error);
      }
    };

    fetchComponents();
  }, [task]);

  const { defaultValues, modelSchema, yupSchema, loading } = useSchema({
    modelName: model,
  });

  useEffect(() => {
    const total = datasetInfo?.total_columns;
    setInputColumns(
      savedConfig?.input_columns?.join(",") || (total ? `1-${total - 1}` : ""),
    );
    setOutputColumns(
      savedConfig?.output_columns?.join(",") || (total ? `${total}` : ""),
    );
    setSplits(
      savedConfig?.splits || {
        train: 0.6,
        validation: 0.2,
        test: 0.2,
        shuffle: true,
        stratify: false,
        splitType: "random",
      },
    );
    setTask(savedConfig?.task || "");
    setModel(savedConfig?.model || "");
    setMetrics(savedConfig?.metrics || []);
    setModelParams(savedConfig?.parameters || {});
  }, [savedConfig, datasetInfo]);

  useEffect(() => {
    if (loading || initializedForModelRef.current === model) return;

    if (
      savedConfig?.model === model &&
      savedConfig?.parameters &&
      Object.keys(savedConfig.parameters).length > 0
    ) {
      setModelParams(savedConfig.parameters);
    } else if (defaultValues && Object.keys(defaultValues).length > 0) {
      setModelParams(defaultValues);
    } else {
      setModelParams({});
    }

    initializedForModelRef.current = model;
  }, [loading, model, defaultValues, savedConfig]);

  const handleChange = (newValues) => {
    setModelParams(newValues);
  };

  const handleSave = async () => {
    const maxValue = datasetInfo?.total_columns;
    const parsedInput = inputColumns
      ? parseRangeToIndex(inputColumns, maxValue)
      : [];
    const parsedOutput = outputColumns
      ? parseRangeToIndex(outputColumns, maxValue)
      : [];
    const payload = {
      input_columns: parsedInput,
      output_columns: parsedOutput,
      splits: {
        train: splits.train,
        validation: splits.validation,
        test: splits.test,
        shuffle: splits.shuffle,
        stratify: splits.stratify,
        splitType: splits.splitType,
      },
      task: task,
      model: model,
      metrics: metrics,
      parameters: modelParams,
    };

    try {
      const response = await validateNode("Train", payload);
      if (response.status === "ok") {
        setValidationStatus("ok");
        onSave(payload);
        onClose();
      } else {
        setValidationStatus("error");
        enqueueSnackbar("Validation failed", { variant: "error" });
      }
    } catch (e) {
      setValidationStatus("error");
      enqueueSnackbar("Error validating node", { variant: "error" });
      console.error(e);
    }
  };

  const getDatasetInfo = async () => {
    setInfoLoading(true);
    try {
      const datasetInfo = await getDatasetInfoRequest(datasetId);
      setDatasetInfo(datasetInfo);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset info.");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setInfoLoading(false);
    }
  };

  useEffect(() => {
    if (!datasetId) {
      setInfoLoading(false);
      return;
    }
    getDatasetInfo();
  }, [datasetId]);

  const hasWarnedRef = useRef(false);

  useEffect(() => {
    const validateAvailableTasks = async () => {
      if (!datasetId) {
        if (!hasWarnedRef.current) {
          enqueueSnackbar("Missing dataset", { variant: "warning" });
          hasWarnedRef.current = true;
        }
        setValidTasks([]);
        return;
      }

      const maxValue = datasetInfo?.total_columns;
      let input = [];
      let output = [];
      let parseError = false;

      try {
        input = inputColumns ? parseRangeToIndex(inputColumns, maxValue) : [];
        setInputError(false);
        setInputErrorMessage("");
      } catch (err) {
        setInputError(true);
        setInputErrorMessage(err.message);
        parseError = true;
      }

      try {
        output = outputColumns
          ? parseRangeToIndex(outputColumns, maxValue)
          : [];
        setOutputError(false);
        setOutputErrorMessage("");
      } catch (err) {
        setOutputError(true);
        setOutputErrorMessage(err.message);
        parseError = true;
      }

      if (parseError) {
        setValidTasks([]);
        return;
      }

      const results = await Promise.all(
        availableTasks.map(async (taskObj) => {
          try {
            const validation = await validateColumnsRequest(
              taskObj.name,
              datasetId,
              input,
              output,
            );
            return validation.dataset_status === "valid" ? taskObj.name : null;
          } catch (error) {
            console.warn(`Error validating task ${taskObj.name}`, error);
            return null;
          }
        }),
      );

      const valid = results.filter(Boolean);
      setValidTasks(valid);
    };

    validateAvailableTasks();
  }, [availableTasks, inputColumns, outputColumns, datasetId, datasetInfo]);

  return (
    <>
      <DialogContent>
        <Grid container>
          <Grid size={{ xs: 12 }}>
            <Typography variant="body1">Split Data:</Typography>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }} sx={{ pr: 2 }}>
            <TextField
              label="Input Columns"
              fullWidth
              value={inputColumns}
              onChange={(e) => setInputColumns(e.target.value)}
              margin="normal"
              error={inputError}
              helperText={inputError ? inputErrorMessage : ""}
            />
            <TextField
              label="Output Columns"
              fullWidth
              value={outputColumns}
              onChange={(e) => setOutputColumns(e.target.value)}
              margin="normal"
              error={outputError}
              helperText={outputError ? outputErrorMessage : ""}
            />

            <Grid size={{ xs: 12 }} sx={{ mt: 3 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={splits.shuffle}
                    onChange={(e) =>
                      setSplits({ ...splits, shuffle: e.target.checked })
                    }
                  />
                }
                label="Shuffle"
                sx={{ ml: 1 }}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={splits.stratify}
                    onChange={(e) =>
                      setSplits({ ...splits, stratify: e.target.checked })
                    }
                  />
                }
                label="Stratify"
              />
            </Grid>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Training"
              type="number"
              fullWidth
              value={splits.train}
              onChange={(e) =>
                setSplits({ ...splits, train: parseFloat(e.target.value, 10) })
              }
              margin="normal"
            />
            <TextField
              label="Validation"
              type="number"
              fullWidth
              value={splits.validation}
              onChange={(e) =>
                setSplits({
                  ...splits,
                  validation: parseFloat(e.target.value, 10),
                })
              }
              margin="normal"
            />
            <TextField
              label="Testing"
              type="number"
              fullWidth
              value={splits.test}
              onChange={(e) =>
                setSplits({ ...splits, test: parseFloat(e.target.value, 10) })
              }
              margin="normal"
            />
          </Grid>

          <Grid size={{ xs: 12 }} sx={{ mt: 2 }}>
            <Typography variant="body1">Task and Model:</Typography>
          </Grid>

          <Grid size={{ xs: 12 }}>
            <TextField
              label="Task"
              select
              fullWidth
              value={task}
              onChange={(e) => {
                setTask(e.target.value);
                setModel("");
                setMetrics([]);
                setModelParams({});
              }}
              margin="normal"
            >
              {availableTasks.map((taskObj) => (
                <MenuItem
                  key={taskObj.name}
                  value={taskObj.name}
                  disabled={!validTasks.includes(taskObj.name)}
                >
                  {taskObj.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 12 }}>
            <Grid container spacing={1} alignItems="center">
              <Grid size={{ xs: 12 }}>
                <TextField
                  label="Model"
                  select
                  fullWidth
                  value={model}
                  onChange={(e) => {
                    setModel(e.target.value);
                  }}
                  margin="normal"
                  disabled={!task}
                >
                  {availableModels.map((model) => (
                    <MenuItem key={model.name} value={model.name}>
                      {model.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid>
                <IconButton
                  onClick={() => setOpenSettings(true)}
                  disabled={!model}
                  aria-label="model settings"
                  sx={{ mt: "8px" }}
                >
                  <SettingsIcon />
                </IconButton>
              </Grid>
            </Grid>
          </Grid>

          <Grid size={{ xs: 12 }} sx={{ mt: 2 }}>
            <Typography variant="body1">Metrics:</Typography>
          </Grid>

          <Grid size={{ xs: 12 }}>
            <TextField
              label="Metrics"
              select
              fullWidth
              value={metrics}
              onChange={(e) => setMetrics(e.target.value)}
              margin="normal"
              disabled={!task}
              slotProps={{
                select: { multiple: true },
              }}
            >
              {availableMetrics.map((metric) => (
                <MenuItem key={metric.name} value={metric.name}>
                  {metric.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>

        <Box mt={3}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            onClick={handleSave}
            disabled={
              loading ||
              inputColumns.length === 0 ||
              outputColumns.length === 0 ||
              splits.train + splits.validation + splits.test !== 1 ||
              !task ||
              !model ||
              metrics.length === 0
            }
          >
            Save
          </Button>
        </Box>
      </DialogContent>

      <ParamsSettings
        open={openSettings}
        modelSchema={modelSchema}
        values={modelParams}
        onChange={handleChange}
        onClose={() => setOpenSettings(false)}
      />
    </>
  );
};

Train.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  savedConfig: PropTypes.object,
  prevNodes: PropTypes.arrayOf(PropTypes.object),
};

Train.defaultProps = {
  savedConfig: null,
  prevNodes: [],
};

export default Train;
