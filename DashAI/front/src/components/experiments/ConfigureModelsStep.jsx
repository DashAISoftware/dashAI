import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import {
  Button,
  Grid,
  MenuItem,
  TextField,
  Typography,
  Alert,
  Box,
  Chip,
  Collapse,
} from "@mui/material";
import { useSnackbar } from "notistack";
import PropTypes from "prop-types";
import React, { useEffect, useState, useMemo } from "react";
import uuid from "react-uuid";
import { getComponents as getComponentsRequest } from "../../api/component";
import ModelsTable from "./ModelsTable";
import useSchema from "../../hooks/useSchema";
import { generateSequentialName } from "../../utils/nameGenerator";
import { useTourContext } from "../tour/TourProvider";
import { useTranslation } from "react-i18next";

// Model hints for forecasting models - helps users understand model requirements
const FORECASTING_MODEL_HINTS = {
  ProphetModel: {
    minDataPoints: 30,
    description: "Facebook's Prophet model for business time series",
    strengths: [
      "Handles missing data",
      "Automatic seasonality",
      "Good for daily/weekly patterns",
    ],
    limitations: [
      "Needs consistent frequency",
      "Better with >2 years of data for yearly seasonality",
    ],
    smallDatasetNote:
      "Works with small datasets but yearly seasonality detection may be limited.",
  },
  StatsmodelsSARIMAXModel: {
    minDataPoints: 20,
    description: "Statistical ARIMA/SARIMAX model",
    strengths: [
      "Classic statistical approach",
      "Interpretable parameters",
      "Good for stationary data",
    ],
    limitations: ["Requires parameter tuning", "Sensitive to non-stationarity"],
    smallDatasetNote:
      "With small datasets, seasonality will be auto-disabled and simpler ARIMA will be used.",
  },
  SklearnMultiStepForecaster: {
    minDataPoints: 10,
    description: "Machine learning-based forecaster using sklearn regressors",
    strengths: ["Flexible", "Works with small datasets", "Fast training"],
    limitations: [
      "May overfit with very few samples",
      "No built-in seasonality",
    ],
    smallDatasetNote:
      "Recommended for small datasets. Window size auto-adjusts based on available data.",
  },
};

/**
 * Step of the experiment modal: add models to the experiment and configure its parameters
 * @param {object} newExp object that contains the Experiment Modal state
 * @param {function} setNewExp updates the Eperimento Modal state (newExp)
 * @param {function} setNextEnabled function to enable or disable the "Next" button in the modal
 */
function ConfigureModelsStep({ newExp, setNewExp, setNextEnabled }) {
  const { enqueueSnackbar } = useSnackbar();
  const [name, setName] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [compatibleModels, setCompatibleModels] = useState([]);
  const [hasUserTouchedName, setHasUserTouchedName] = useState(false);
  const tourContext = useTourContext();
  const { t } = useTranslation(["experiments", "common"]);

  const { defaultValues } = useSchema({ modelName: selectedModel });

  const { defaultName } = useMemo(() => {
    if (!selectedModel) {
      return { defaultName: "" };
    }

    return generateSequentialName({
      base: selectedModel,
      items: newExp.runs,
      getName: (run) => run.name,
      filter: (run) => run.model === selectedModel,
    });
  }, [selectedModel, newExp.runs]);

  const getCompatibleModels = async () => {
    try {
      const models = await getComponentsRequest({
        selectTypes: ["Model"],
        relatedComponent: newExp.task_name,
      });
      setCompatibleModels(models);
    } catch (error) {
      enqueueSnackbar(t("experiments:error.fetchingCompatibleModels"), {
        variant: "error",
      });
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };

  const handleAddButton = () => {
    const modelName = name.trim();

    if (!modelName) {
      setHasUserTouchedName(true);
      return;
    }

    const newModel = {
      id: uuid(),
      name: modelName,
      model: selectedModel,
      params: defaultValues,
      optimizer_name: "OptunaOptimizer",
      optimizer_parameters: {
        n_trials: 10,
        sampler: "TPESampler",
        pruner: "None",
      },
    };

    setNewExp({ ...newExp, runs: [newModel, ...newExp.runs] });
    setHasUserTouchedName(false);
    setName("");
    setSelectedModel("");

    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 300);
    }
  };

  const handleOnChangeModel = (event) => {
    setSelectedModel(event.target.value);
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 300);
    }
  };

  const handleOnOpenMenu = () => {
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }
  };

  const getNameError = () => {
    if (!selectedModel || selectedModel.trim() === "") {
      return null;
    }

    if (hasUserTouchedName) {
      const currentName = name.trim();
      if (!currentName) {
        return "Name is required";
      }
    }

    return null;
  };

  const nameError = getNameError();

  useEffect(() => {
    if (newExp.runs.length) {
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [newExp]);

  // in mount, fetches the compatible models with the previously selected task
  useEffect(() => {
    getCompatibleModels();
  }, []);

  useEffect(() => {
    if (!selectedModel) {
      setHasUserTouchedName(false);
      setName("");
    } else if (defaultName) {
      setName(defaultName);
      setHasUserTouchedName(false);
    }
  }, [selectedModel, defaultName]);

  // Check if this is a forecasting task
  const isForecastingTask = newExp.task_name === "ForecastingTask";

  // Get dataset size from splits info (approximate)
  const datasetSize = useMemo(() => {
    if (newExp.splits && newExp.splits.train) {
      // If we have percentage splits, we can estimate from the dataset
      // This is a rough estimate - the actual size comes from the dataset
      return newExp.dataset?.total_rows || null;
    }
    return null;
  }, [newExp.splits, newExp.dataset]);

  // Get model hint if available
  const selectedModelHint = selectedModel
    ? FORECASTING_MODEL_HINTS[selectedModel]
    : null;

  return (
    <Grid
      container
      direction="row"
      justifyContent="space-around"
      alignItems="stretch"
      spacing={2}
    >
      <Grid size={{ xs: 12 }}>
        <Typography variant="subtitle1" component="h3">
          {t("experiments:label.addModelsToExperiment")}
        </Typography>
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Grid
          container
          direction="row"
          columnSpacing={3}
          rowSpacing={3}
          wrap="wrap"
        >
          <Grid size={{ xs: 4, md: 12 }}>
            <TextField
              label={t("experiments:label.modelName")}
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (!hasUserTouchedName) {
                  setHasUserTouchedName(true);
                }
              }}
              onBlur={() => setHasUserTouchedName(true)}
              error={Boolean(
                selectedModel && selectedModel.trim() !== "" && nameError,
              )}
              helperText={
                selectedModel && selectedModel.trim() !== "" ? nameError : ""
              }
              fullWidth
              disabled={!selectedModel}
              placeholder={
                !selectedModel
                  ? t("experiments:label.selectModelFirst")
                  : t("experiments:label.modelName")
              }
              slotProps={{
                inputLabel: { shrink: true },
              }}
            />
          </Grid>

          <Grid size={{ xs: 4, md: 12 }}>
            <TextField
              data-tour="exp-model-selector"
              select
              label={t("experiments:label.selectModelToAdd")}
              value={selectedModel}
              onChange={handleOnChangeModel}
              fullWidth
              slotProps={{
                select: {
                  onOpen: handleOnOpenMenu,
                },
              }}
            >
              {compatibleModels.length === 0 && (
                <MenuItem value="" disabled>
                  {t("experiments:label.noModelsAvailable")}
                </MenuItem>
              )}
              {compatibleModels.length > 0 &&
                compatibleModels.map((model) => (
                  <MenuItem
                    key={model.name}
                    value={model.name}
                    data-tour={`exp-model-option-${model.name}`}
                  >
                    {model.display_name || model.name}
                  </MenuItem>
                ))}
            </TextField>
          </Grid>

          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-end",
              width: "100%",
            }}
          >
            <Button
              data-tour="exp-add-model-button"
              variant="outlined"
              disabled={selectedModel === "" || name.trim() === ""}
              startIcon={<AddIcon />}
              onClick={handleAddButton}
              sx={{ height: "100%" }}
            >
              {t("common:add")}
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Model Info Panel for Forecasting */}
      <Collapse
        in={isForecastingTask && selectedModel && selectedModelHint}
        sx={{ width: "100%" }}
      >
        <Grid size={{ xs: 12 }}>
          <Alert severity="info" icon={<InfoOutlinedIcon />} sx={{ mt: 1 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {selectedModelHint?.description}
            </Typography>

            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 1 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Strengths:
                </Typography>
                <Box
                  sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}
                >
                  {selectedModelHint?.strengths.map((s, i) => (
                    <Chip
                      key={i}
                      label={s}
                      size="small"
                      color="success"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </Box>
            </Box>

            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 1 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Limitations:
                </Typography>
                <Box
                  sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}
                >
                  {selectedModelHint?.limitations.map((l, i) => (
                    <Chip
                      key={i}
                      label={l}
                      size="small"
                      color="warning"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </Box>
            </Box>

            {selectedModelHint?.smallDatasetNote && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                💡 <strong>Small dataset tip:</strong>{" "}
                {selectedModelHint.smallDatasetNote}
              </Typography>
            )}
          </Alert>
        </Grid>
      </Collapse>

      {/* Models table */}
      <Grid size={{ xs: 12 }} data-tour="models-table">
        <ModelsTable newExp={newExp} setNewExp={setNewExp} />
      </Grid>
    </Grid>
  );
}

ConfigureModelsStep.propTypes = {
  newExp: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    dataset: PropTypes.object,
    task_name: PropTypes.string,
    input_columns: PropTypes.arrayOf(PropTypes.string),
    output_columns: PropTypes.arrayOf(PropTypes.string),
    splits: PropTypes.shape({
      training: PropTypes.number,
      validation: PropTypes.number,
      testing: PropTypes.number,
    }),
    step: PropTypes.string,
    created: PropTypes.instanceOf(Date),
    last_modified: PropTypes.instanceOf(Date),
    runs: PropTypes.array,
  }),
  setNewExp: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

export default ConfigureModelsStep;
