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
} from "@mui/material";
import SettingsIcon from "@mui/icons-material/Settings";
import useSchema from "../../../hooks/useSchema";
import ParamsSettings from "../ParamsSettings";
import { getComponents as getComponentsRequest } from "../../../api/component";
import { validateColumns as validateColumnsRequest } from "../../../api/modelSession";
import { getDatasetInfo as getDatasetInfoRequest } from "../../../api/datasets";
import { validateNode } from "../../../api/pipeline";
import { parseRangeToIndex } from "../../../utils/parseRange";
import { useSnackbar } from "notistack";

/**
 * TaskAndModelNode – selects ML task & model, configures hyper-parameters.
 *
 * Receives from SplitData (via prevNodes):
 *   input_columns, output_columns, splits, id (dataset id), file_path
 */
const TaskAndModelNode = ({
  open,
  onClose,
  onSave,
  savedConfig,
  prevNodes,
}) => {
  const [task, setTask] = useState(savedConfig?.task || "");
  const [model, setModel] = useState(savedConfig?.model || "");
  const [openSettings, setOpenSettings] = useState(false);
  const [modelParams, setModelParams] = useState(savedConfig?.parameters || {});
  const [initialized, setInitialized] = useState(false);

  const [availableTasks, setAvailableTasks] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [validTasks, setValidTasks] = useState([]);
  const [validationErrors, setValidationErrors] = useState({});

  const [datasetInfo, setDatasetInfo] = useState({});
  const [infoLoading, setInfoLoading] = useState(true);

  const { enqueueSnackbar } = useSnackbar();
  const hasWarnedRef = useRef(false);

  // Try to locate the dataset info from a SplitData or DataSelector upstream
  const splitDataNode = prevNodes?.find(
    (node) => node?.input_columns || node?.splits,
  );
  const datasetNode = prevNodes?.find((node) => node?.file_path && node?.id);
  const datasetId = datasetNode?.id ?? null;
  const inputColumnsRaw = splitDataNode?.input_columns;
  const outputColumnsRaw = splitDataNode?.output_columns;

  // ---------- Fetch dataset info ----------
  useEffect(() => {
    if (!datasetId) {
      setInfoLoading(false);
      if (!hasWarnedRef.current) {
        enqueueSnackbar("Missing dataset – connect a SplitData node first.", {
          variant: "warning",
        });
        hasWarnedRef.current = true;
      }
      return;
    }
    const fetchInfo = async () => {
      setInfoLoading(true);
      try {
        const info = await getDatasetInfoRequest(datasetId);
        setDatasetInfo(info);
      } catch (error) {
        enqueueSnackbar("Error fetching dataset info.", { variant: "error" });
        console.error(error);
      } finally {
        setInfoLoading(false);
      }
    };
    fetchInfo();
  }, [datasetId]);

  // ---------- Fetch available tasks / models ----------
  useEffect(() => {
    const fetchComponents = async () => {
      try {
        const tasks = await getComponentsRequest({ selectTypes: ["Task"] });
        const models = await getComponentsRequest({
          selectTypes: ["Model"],
          relatedComponent: task,
        });
        setAvailableTasks(tasks);
        setAvailableModels(models);
      } catch (error) {
        console.error("Error fetching components:", error);
      }
    };
    fetchComponents();
  }, [task]);

  // ---------- Model schema ----------
  const { defaultValues, modelSchema, yupSchema, loading } = useSchema({
    modelName: model,
  });

  useEffect(() => {
    if (savedConfig) {
      setTask(savedConfig.task || "");
      setModel(savedConfig.model || "");
      setModelParams(savedConfig.parameters || {});
    }
  }, [savedConfig]);

  useEffect(() => {
    setInitialized(false);
  }, [model]);

  useEffect(() => {
    if (loading || initialized) return;
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
    setInitialized(true);
  }, [loading, model, defaultValues, savedConfig, initialized]);

  const handleChange = (newValues) => setModelParams(newValues);

  // ---------- Validate available tasks against columns ----------
  useEffect(() => {
    const validateAvailableTasks = async () => {
      if (!datasetId || !inputColumnsRaw || !outputColumnsRaw) {
        setValidTasks([]);
        return;
      }

      const maxValue = datasetInfo?.total_columns;
      const columnNames = datasetInfo?.column_names || [];

      // inputColumnsRaw may be an array of indices already (from SplitData)
      let inputColumnNames;
      let outputColumnNames;
      if (Array.isArray(inputColumnsRaw)) {
        inputColumnNames = inputColumnsRaw.map(
          (idx) => columnNames[idx - 1] || `Column_${idx}`,
        );
        outputColumnNames = (outputColumnsRaw || []).map(
          (idx) => columnNames[idx - 1] || `Column_${idx}`,
        );
      } else {
        try {
          const parsedInput = parseRangeToIndex(
            String(inputColumnsRaw),
            maxValue,
          );
          const parsedOutput = parseRangeToIndex(
            String(outputColumnsRaw),
            maxValue,
          );
          inputColumnNames = parsedInput.map(
            (idx) => columnNames[idx - 1] || `Column_${idx}`,
          );
          outputColumnNames = parsedOutput.map(
            (idx) => columnNames[idx - 1] || `Column_${idx}`,
          );
        } catch {
          setValidTasks([]);
          return;
        }
      }

      const results = await Promise.all(
        availableTasks.map(async (taskObj) => {
          try {
            const validation = await validateColumnsRequest(
              taskObj.name,
              datasetId,
              inputColumnNames,
              outputColumnNames,
            );
            if (validation.dataset_status === "valid") {
              return { name: taskObj.name, valid: true };
            }
            return {
              name: taskObj.name,
              valid: false,
              error: validation.error,
            };
          } catch (error) {
            return {
              name: taskObj.name,
              valid: false,
              error: "Request failed",
            };
          }
        }),
      );

      const validList = results.filter((r) => r.valid).map((r) => r.name);
      const errorsMap = {};
      results.forEach((r) => {
        if (!r.valid) errorsMap[r.name] = r.error;
      });
      setValidationErrors(errorsMap);
      setValidTasks(validList);
    };

    validateAvailableTasks();
  }, [
    availableTasks,
    inputColumnsRaw,
    outputColumnsRaw,
    datasetId,
    datasetInfo,
  ]);

  // ---------- Save ----------
  const handleSave = async () => {
    const payload = {
      task,
      model,
      parameters: modelParams,
    };

    try {
      const response = await validateNode("TaskAndModel", payload);
      if (response.status === "ok") {
        onSave(payload);
        onClose();
      } else {
        enqueueSnackbar(response.message || "Validation failed", {
          variant: "error",
        });
      }
    } catch (e) {
      enqueueSnackbar("Error validating node", { variant: "error" });
      console.error(e);
    }
  };

  return (
    <>
      <DialogContent
        sx={{
          width: { xs: "100%", md: 760 },
          maxWidth: "100%",
        }}
      >
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              Task and Model
            </Typography>
          </Grid>

          {validTasks.length === 0 &&
            Object.keys(validationErrors).length > 0 && (
              <Grid item xs={12}>
                <Typography
                  variant="body2"
                  sx={{ color: "warning.main", mb: 1 }}
                >
                  ⚠️ No compatible tasks available. Validation errors:
                </Typography>
                {Object.entries(validationErrors).map(([taskName, error]) => (
                  <Typography
                    key={taskName}
                    variant="caption"
                    sx={{ display: "block", mb: 0.5 }}
                  >
                    <strong>{taskName}:</strong> {error}
                  </Typography>
                ))}
              </Grid>
            )}

          <Grid item xs={12}>
            <Grid container spacing={1.5} alignItems="center">
              <Grid item xs={11}>
                <TextField
                  label="Task"
                  select
                  fullWidth
                  value={task}
                  onChange={(e) => {
                    setTask(e.target.value);
                    setModel("");
                    setModelParams({});
                  }}
                  margin="normal"
                  disabled={validTasks.length === 0}
                  slotProps={{
                    select: {
                      MenuProps: {
                        PaperProps: {
                          sx: {
                            maxHeight: 420,
                            minWidth: 560,
                          },
                        },
                      },
                    },
                  }}
                  sx={{
                    minWidth: { xs: "100%", md: 560 },
                    "& .MuiInputBase-root": {
                      minHeight: 58,
                    },
                    "& .MuiSelect-select": {
                      whiteSpace: "normal",
                      minHeight: "1.4375em !important",
                      display: "flex",
                      alignItems: "center",
                    },
                  }}
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
              <Grid item xs={1}>
                <IconButton
                  onClick={() => setOpenSettings(true)}
                  disabled={!model}
                  aria-label="model settings"
                  sx={{ mt: "8px", ml: { xs: 0, md: 0.5 } }}
                >
                  <SettingsIcon />
                </IconButton>
              </Grid>
            </Grid>
          </Grid>

          <Grid item xs={12}>
            <Grid container spacing={1.5} alignItems="center">
              <Grid item xs={11}>
                <TextField
                  label="Model"
                  select
                  fullWidth
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  margin="normal"
                  disabled={!task}
                  slotProps={{
                    select: {
                      MenuProps: {
                        PaperProps: {
                          sx: {
                            maxHeight: 420,
                            minWidth: 560,
                          },
                        },
                      },
                    },
                  }}
                  sx={{
                    minWidth: { xs: "100%", md: 560 },
                    "& .MuiInputBase-root": {
                      minHeight: 58,
                    },
                    "& .MuiSelect-select": {
                      whiteSpace: "normal",
                      minHeight: "1.4375em !important",
                      display: "flex",
                      alignItems: "center",
                    },
                  }}
                >
                  {availableModels.map((m) => (
                    <MenuItem key={m.name} value={m.name}>
                      {m.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid item xs={1} />
            </Grid>
          </Grid>
        </Grid>

        <Box mt={3}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            onClick={handleSave}
            disabled={loading || !task || !model}
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

TaskAndModelNode.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  savedConfig: PropTypes.object,
  prevNodes: PropTypes.arrayOf(PropTypes.object),
};

TaskAndModelNode.defaultProps = {
  savedConfig: null,
  prevNodes: [],
};

export default TaskAndModelNode;
