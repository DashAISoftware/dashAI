import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import { Button, Grid, MenuItem, TextField, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import PropTypes from "prop-types";
import React, { useEffect, useState, useMemo } from "react";
import uuid from "react-uuid";
import { getComponents as getComponentsRequest } from "../../api/component";
import ModelsTable from "./ModelsTable";
import useSchema from "../../hooks/useSchema";
import { generateSequentialName } from "../../utils/nameGenerator";
import { useTourContext } from "../tour/TourProvider";

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
      enqueueSnackbar("Error while trying to obtain compatible models");
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
          Add models to your experiment
        </Typography>
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Grid container direction="row" columnSpacing={3} wrap="nowrap">
          <Grid size={{ xs: 4, md: 12 }}>
            <TextField
              label="Model Name"
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
                !selectedModel ? "Select a model first" : "Model Name"
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
              label="Select a model to add"
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
                  No models available
                </MenuItem>
              )}
              {compatibleModels.length > 0 &&
                compatibleModels.map((model) => (
                  <MenuItem
                    key={model.name}
                    value={model.name}
                    data-tour={`exp-model-option-${model.name}`}
                  >
                    {model.name}
                  </MenuItem>
                ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 1, md: 2 }}>
            <Button
              data-tour="exp-add-model-button"
              variant="outlined"
              disabled={selectedModel === "" || name.trim() === ""}
              startIcon={<AddIcon />}
              onClick={handleAddButton}
              sx={{ height: "100%" }}
            >
              Add
            </Button>
          </Grid>
        </Grid>
      </Grid>
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
    input_columns: PropTypes.arrayOf(PropTypes.number),
    output_columns: PropTypes.arrayOf(PropTypes.number),
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
