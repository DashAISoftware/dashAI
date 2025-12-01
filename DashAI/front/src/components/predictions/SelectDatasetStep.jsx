import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import {
  Alert,
  AlertTitle,
  Box,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  Grid,
  Link,
  Paper,
  Radio,
  RadioGroup,
  TextField,
  Typography,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import { Link as RouterLink } from "react-router-dom";
import PredictionNameInput from "./PredictionNameInput";
import InfoIcon from "@mui/icons-material/Info";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import UploadFileIcon from "@mui/icons-material/UploadFile";

import {
  getDatasets as getDatasetsRequest,
  getDatasetTemporalInfo,
} from "../../api/datasets";

import { filter_datasets as filterDatasetsRequest } from "../../api/predict";
import { formatDate } from "../../utils";

const columns = [
  {
    field: "name",
    headerName: "Name",
    minWidth: 250,
    editable: false,
  },
  {
    field: "created",
    headerName: "Created",
    minWidth: 200,
    type: Date,
    valueFormatter: (params) => formatDate(params.value),
    editable: false,
  },
  {
    field: "last_modified",
    headerName: "Last modified",
    minWidth: 200,
    type: Date,
    valueFormatter: (params) => formatDate(params.value),
    editable: false,
  },
];

function SelectDatasetStep({
  selectedModelId,
  preselectedModelId,
  setSelectedDatasetId,
  setNextEnabled,
  trainDataset,
  defaultName,
  handlePredictNameInput,
  predictName,
  selectedTaskName,
  forecastPeriods,
  setForecastPeriods,
  temporalInfo,
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [datasetsSelected, setDatasetsSelected] = useState([]);
  const [requestError, setRequestError] = useState(false);
  const [isNameValid, setIsNameValid] = useState(false);
  const [selectedDatasetTemporalInfo, setSelectedDatasetTemporalInfo] =
    useState(null);
  const [frequencyMismatch, setFrequencyMismatch] = useState(false);
  const [loadingTemporalInfo, setLoadingTemporalInfo] = useState(false);
  // For forecasting: track which prediction mode is selected
  const [forecastMode, setForecastMode] = useState("dataset"); // "dataset" or "auto-generate"

  const isForecastingTask = selectedTaskName === "ForecastingTask";

  const getDatasets = async () => {
    setLoading(true);
    try {
      const requestData = {
        run_id: preselectedModelId ?? selectedModelId,
      };
      const filteredDatasets = await filterDatasetsRequest(requestData);
      setDatasets(filteredDatasets);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the datasets list.");
      setRequestError(true);

      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getDatasets();
  }, []);

  // Validate temporal frequency when a dataset is selected for forecasting
  useEffect(() => {
    const validateSelectedDatasetFrequency = async () => {
      if (
        !isForecastingTask ||
        datasetsSelected.length === 0 ||
        !temporalInfo
      ) {
        setSelectedDatasetTemporalInfo(null);
        setFrequencyMismatch(false);
        return;
      }

      const selectedId = datasetsSelected[0];
      setLoadingTemporalInfo(true);

      try {
        // Use the same timestamp column as the training dataset
        const timestampColumn = temporalInfo.timestamp_column;
        const predictionDatasetInfo = await getDatasetTemporalInfo(
          selectedId,
          timestampColumn,
        );
        setSelectedDatasetTemporalInfo(predictionDatasetInfo);

        // Compare frequencies
        if (
          predictionDatasetInfo.frequency_code !== temporalInfo.frequency_code
        ) {
          setFrequencyMismatch(true);
          console.warn(
            `[SelectDatasetStep] Frequency mismatch! Training: ${temporalInfo.frequency_code}, Prediction dataset: ${predictionDatasetInfo.frequency_code}`,
          );
        } else {
          setFrequencyMismatch(false);
        }
      } catch (error) {
        console.error("Error validating prediction dataset frequency:", error);
        setSelectedDatasetTemporalInfo(null);
        setFrequencyMismatch(false);
      } finally {
        setLoadingTemporalInfo(false);
      }
    };

    validateSelectedDatasetFrequency();
  }, [datasetsSelected, isForecastingTask, temporalInfo]);

  useEffect(() => {
    // For ForecastingTask: enable Next based on selected mode
    // But BLOCK if there's a frequency mismatch (only applies to dataset mode)

    if (isForecastingTask) {
      if (forecastMode === "auto-generate") {
        // Auto-generate mode: need forecast_periods > 0
        if (forecastPeriods > 0) {
          setSelectedDatasetId(null); // Clear dataset selection
          setNextEnabled(preselectedModelId ? isNameValid : true);
        } else {
          setNextEnabled(false);
        }
      } else {
        // Dataset mode: need dataset selected and no frequency mismatch
        if (frequencyMismatch) {
          setNextEnabled(false);
        } else if (datasetsSelected.length > 0) {
          const selectedDatasetId = datasetsSelected[0];
          setSelectedDatasetId(selectedDatasetId);
          setForecastPeriods(null); // Clear auto-generate when using dataset
          setNextEnabled(preselectedModelId ? isNameValid : true);
        } else {
          setNextEnabled(false);
        }
      }
    } else {
      // Non-forecasting tasks: just need dataset selected
      if (datasetsSelected.length > 0) {
        const selectedDatasetId = datasetsSelected[0];
        setSelectedDatasetId(selectedDatasetId);
        setNextEnabled(preselectedModelId ? isNameValid : true);
      } else {
        setNextEnabled(false);
      }
    }
  }, [
    datasetsSelected,
    isNameValid,
    preselectedModelId,
    isForecastingTask,
    forecastPeriods,
    frequencyMismatch,
    forecastMode,
  ]);

  return (
    <React.Fragment>
      {preselectedModelId && (
        <Grid item xs={12}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
            Provide a prediction name to continue and select a dataset
          </Typography>

          <PredictionNameInput
            defaultPredictionName={defaultName}
            onValidChange={setIsNameValid}
            onNameChange={handlePredictNameInput}
          />
        </Grid>
      )}

      {isForecastingTask && temporalInfo && (
        <Grid item xs={12} sx={{ mb: 2 }}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              bgcolor: "success.50",
              border: "1px solid",
              borderColor: "success.200",
              borderRadius: 2,
            }}
          >
            <Typography
              variant="subtitle2"
              sx={{ mb: 1.5, display: "flex", alignItems: "center", gap: 1 }}
            >
              <TrendingUpIcon fontSize="small" color="success" />
              Training Data Time Series Properties
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <AccessTimeIcon fontSize="small" color="action" />
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Frequency
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      <Chip
                        label={temporalInfo.frequency_label}
                        size="small"
                        color="success"
                        sx={{ mr: 0.5 }}
                      />
                    </Typography>
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <CalendarTodayIcon fontSize="small" color="action" />
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Training Period
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {new Date(temporalInfo.start_date).toLocaleDateString()} →{" "}
                      {new Date(temporalInfo.end_date).toLocaleDateString()}
                    </Typography>
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Training Periods
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {temporalInfo.total_periods}{" "}
                    {temporalInfo.frequency_label.toLowerCase()}
                  </Typography>
                </Box>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Average Interval
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {temporalInfo.average_interval}
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                <strong>What this means:</strong> The model was trained on{" "}
                <strong>{temporalInfo.frequency_label.toLowerCase()}</strong>{" "}
                data. Each prediction step will forecast{" "}
                <strong>
                  1 {temporalInfo.frequency_label.toLowerCase().slice(0, -2)}
                </strong>{" "}
                into the future. {temporalInfo.frequency_example}
              </Typography>
            </Alert>
          </Paper>
        </Grid>
      )}

      {/* Forecasting Mode Selection */}
      {isForecastingTask && (
        <Grid item xs={12} sx={{ mb: 3 }}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
            }}
          >
            <Typography variant="subtitle1" fontWeight="medium" sx={{ mb: 2 }}>
              Choose Prediction Method
            </Typography>

            <FormControl component="fieldset" fullWidth>
              <RadioGroup
                value={forecastMode}
                onChange={(e) => {
                  setForecastMode(e.target.value);
                  // Clear the other option when switching
                  if (e.target.value === "auto-generate") {
                    setDatasetsSelected([]);
                    setSelectedDatasetTemporalInfo(null);
                    setFrequencyMismatch(false);
                  } else {
                    setForecastPeriods(null);
                  }
                }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    mb: 2,
                    border: "2px solid",
                    borderColor:
                      forecastMode === "auto-generate"
                        ? "primary.main"
                        : "divider",
                    borderRadius: 2,
                    bgcolor:
                      forecastMode === "auto-generate"
                        ? "primary.50"
                        : "transparent",
                    cursor: "pointer",
                  }}
                  onClick={() => {
                    setForecastMode("auto-generate");
                    setDatasetsSelected([]);
                    setSelectedDatasetTemporalInfo(null);
                    setFrequencyMismatch(false);
                  }}
                >
                  <FormControlLabel
                    value="auto-generate"
                    control={<Radio />}
                    label={
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <AutoAwesomeIcon
                          color={
                            forecastMode === "auto-generate"
                              ? "primary"
                              : "action"
                          }
                        />
                        <Box>
                          <Typography variant="subtitle2" fontWeight="medium">
                            Auto-generate Future Timestamps
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Automatically generate future dates from the last
                            training date.
                            {temporalInfo &&
                              ` Starting from ${new Date(temporalInfo.end_date).toLocaleDateString()}.`}
                          </Typography>
                        </Box>
                      </Box>
                    }
                    sx={{ m: 0, width: "100%" }}
                  />

                  {forecastMode === "auto-generate" && (
                    <Box sx={{ mt: 2, pl: 4 }}>
                      <TextField
                        fullWidth
                        type="number"
                        size="small"
                        label={
                          temporalInfo
                            ? `Number of Future ${temporalInfo.frequency_label}`
                            : "Number of Future Periods"
                        }
                        placeholder={temporalInfo ? `e.g., 30` : "e.g., 30"}
                        value={forecastPeriods || ""}
                        onChange={(e) => {
                          const value = e.target.value;
                          if (value === "") {
                            setForecastPeriods(null);
                          } else {
                            const numValue = parseInt(value, 10);
                            if (numValue > 0 && numValue <= 1000) {
                              setForecastPeriods(numValue);
                            }
                          }
                        }}
                        helperText={
                          temporalInfo
                            ? `Forecast ${forecastPeriods || "N"} ${temporalInfo.frequency_label.toLowerCase()} into the future`
                            : "How many periods to forecast"
                        }
                        inputProps={{
                          min: 1,
                          max: 1000,
                        }}
                      />
                      <Alert
                        severity="warning"
                        sx={{ mt: 1 }}
                        icon={<InfoIcon />}
                      >
                        <Typography variant="body2">
                          This option is <strong>not available</strong> for
                          models trained with exogenous variables, as future
                          values of those variables are required.
                        </Typography>
                      </Alert>
                    </Box>
                  )}
                </Paper>

                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    border: "2px solid",
                    borderColor:
                      forecastMode === "dataset" ? "primary.main" : "divider",
                    borderRadius: 2,
                    bgcolor:
                      forecastMode === "dataset" ? "primary.50" : "transparent",
                    cursor: "pointer",
                  }}
                  onClick={() => {
                    setForecastMode("dataset");
                    setForecastPeriods(null);
                  }}
                >
                  <FormControlLabel
                    value="dataset"
                    control={<Radio />}
                    label={
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <UploadFileIcon
                          color={
                            forecastMode === "dataset" ? "primary" : "action"
                          }
                        />
                        <Box>
                          <Typography variant="subtitle2" fontWeight="medium">
                            Upload Dataset with Timestamps
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Use a dataset containing specific timestamps you
                            want to predict. Required if the model uses
                            exogenous variables.
                          </Typography>
                        </Box>
                      </Box>
                    }
                    sx={{ m: 0, width: "100%" }}
                  />
                </Paper>
              </RadioGroup>
            </FormControl>
          </Paper>
        </Grid>
      )}

      {/* Dataset requirements info - only show when dataset mode is selected */}
      {isForecastingTask && forecastMode === "dataset" && (
        <Grid item xs={12} sx={{ mb: 2 }}>
          <Alert severity="info" icon={<InfoIcon />}>
            <AlertTitle>Dataset Requirements</AlertTitle>
            <Typography variant="body2" component="div">
              <strong>For forecasting predictions:</strong>
              <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
                <li>
                  Dataset must include a <strong>ds</strong> (timestamp) column
                  with dates to predict (past, present, or future)
                </li>
                <li>
                  Timestamps must be <strong>strictly increasing</strong> and
                  match the training frequency
                  {temporalInfo && (
                    <strong> ({temporalInfo.frequency_label})</strong>
                  )}
                </li>
                <li>
                  If the model used exogenous regressors during training,
                  include those columns with values for all timestamps
                </li>
                <li>
                  Any <strong>y</strong> (target) column will be ignored during
                  prediction
                </li>
              </ul>
            </Typography>
          </Alert>
        </Grid>
      )}

      {/* Dataset selection - show for non-forecasting OR when dataset mode is selected */}
      {(!isForecastingTask || forecastMode === "dataset") && (
        <>
          <Grid
            container
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            sx={{ mb: 4 }}
          >
            <Typography variant="subtitle1" component="h3">
              Select a dataset for{" "}
              {isForecastingTask ? "prediction" : "the selected task"}
            </Typography>
          </Grid>
          {datasets.length === 0 && !loading && !requestError && (
            <React.Fragment>
              <Alert severity="warning" sx={{ mb: 2 }}>
                <AlertTitle>There is no datasets available.</AlertTitle>
                Go to{" "}
                <Link component={RouterLink} to="/app/data">
                  data tab
                </Link>{" "}
                to upload one first.
              </Alert>
              <Typography></Typography>
            </React.Fragment>
          )}
          <Paper>
            <DataGrid
              rows={datasets}
              columns={columns}
              initialState={{
                pagination: {
                  paginationModel: {
                    pageSize: 10,
                  },
                },
              }}
              onRowSelectionModelChange={(newRowSelectionModel) => {
                setDatasetsSelected(newRowSelectionModel);
              }}
              rowSelectionModel={datasetsSelected}
              density="compact"
              pageSizeOptions={[10]}
              loading={loading}
              autoHeight
              hideFooterSelectedRowCount
            />
          </Paper>
        </>
      )}

      {/* Frequency mismatch warning */}
      {isForecastingTask &&
        frequencyMismatch &&
        selectedDatasetTemporalInfo &&
        temporalInfo && (
          <Alert severity="error" icon={<WarningAmberIcon />} sx={{ mt: 2 }}>
            <AlertTitle>Temporal Frequency Mismatch</AlertTitle>
            <Typography variant="body2" component="div">
              The selected dataset has a{" "}
              <strong>different temporal frequency</strong> than the training
              data:
              <Box sx={{ mt: 1, display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Training Data
                  </Typography>
                  <Box>
                    <Chip
                      label={temporalInfo.frequency_label}
                      size="small"
                      color="success"
                      sx={{ mr: 0.5 }}
                    />
                    <Typography variant="caption">
                      ({temporalInfo.average_interval})
                    </Typography>
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Selected Dataset
                  </Typography>
                  <Box>
                    <Chip
                      label={selectedDatasetTemporalInfo.frequency_label}
                      size="small"
                      color="error"
                      sx={{ mr: 0.5 }}
                    />
                    <Typography variant="caption">
                      ({selectedDatasetTemporalInfo.average_interval})
                    </Typography>
                  </Box>
                </Box>
              </Box>
              <Typography variant="body2" sx={{ mt: 1 }}>
                <strong>This will produce incorrect predictions.</strong> Please
                select a dataset with{" "}
                <strong>{temporalInfo.frequency_label.toLowerCase()}</strong>{" "}
                frequency, or use the auto-generate option above.
              </Typography>
            </Typography>
          </Alert>
        )}

      {/* Loading indicator while checking frequency */}
      {isForecastingTask &&
        loadingTemporalInfo &&
        datasetsSelected.length > 0 && (
          <Box sx={{ mt: 2, display: "flex", alignItems: "center", gap: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.secondary">
              Validating dataset temporal frequency...
            </Typography>
          </Box>
        )}

      {/* Success message when frequencies match */}
      {isForecastingTask &&
        !frequencyMismatch &&
        selectedDatasetTemporalInfo &&
        temporalInfo &&
        !loadingTemporalInfo && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Frequency match!</strong> The selected dataset has the
              same temporal frequency (
              <strong>{selectedDatasetTemporalInfo.frequency_label}</strong>) as
              the training data. Period:{" "}
              {new Date(
                selectedDatasetTemporalInfo.start_date,
              ).toLocaleDateString()}{" "}
              →{" "}
              {new Date(
                selectedDatasetTemporalInfo.end_date,
              ).toLocaleDateString()}
              ({selectedDatasetTemporalInfo.total_periods} periods)
            </Typography>
          </Alert>
        )}
    </React.Fragment>
  );
}

SelectDatasetStep.propTypes = {
  setSelectedDatasetId: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  trainDataset: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
    .isRequired,
  selectedTaskName: PropTypes.string,
  defaultName: PropTypes.string,
  handlePredictNameInput: PropTypes.func,
  predictName: PropTypes.string,
  preselectedModelId: PropTypes.number,
  forecastPeriods: PropTypes.number,
  setForecastPeriods: PropTypes.func,
  selectedModelId: PropTypes.number,
  temporalInfo: PropTypes.shape({
    frequency_code: PropTypes.string,
    frequency_label: PropTypes.string,
    frequency_description: PropTypes.string,
    frequency_example: PropTypes.string,
    average_interval: PropTypes.string,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    total_periods: PropTypes.number,
    detected_gaps: PropTypes.number,
    timestamp_column: PropTypes.string,
  }),
};

export default SelectDatasetStep;
