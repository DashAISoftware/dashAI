import { useState, useEffect } from "react";
import PropTypes from "prop-types";

import { CircularProgress, Grid, TextField, Typography } from "@mui/material";
import { useSnackbar } from "notistack";

import { getComponents as getComponentsRequest } from "../../api/component";

import ItemSelectorWithInfo from "../custom/ItemSelectorWithInfo";

function SetNameAndTaskStep({
  newExp,
  setNewExp,
  setNextEnabled,
  defaultExperimentName,
  existingExperiments = [],
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [loading, setLoading] = useState(false);
  const [nModifications, setNModifications] = useState(0);
  const [expNameOk, setExpNameOk] = useState(true);
  const [expNameError, setExpNameError] = useState(false);

  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState({});
  const [taskNameOk, setTaskNameOk] = useState(false);

  // useEffect(() => {
  //   handleNameInputChange({ target: { value: defaultExperimentName } });
  // }, [defaultExperimentName]);

  const getTasks = async () => {
    setLoading(true);
    try {
      const tasks = await getComponentsRequest({
        selectTypes: ["Task"],
        hasRelatedOfType: "Model",
      });
      setTasks(tasks);
      if (typeof newExp.task_name === "string" && newExp.task_name !== "") {
        const previouslySelectedTask =
          tasks.find((task) => task.name === newExp.task_name) || {};
        setSelectedTask(previouslySelectedTask);
      }
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the task list.");
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

  const handleNameInputChange = (event) => {
    const inputValue = event.target.value;
    setNewExp({ ...newExp, name: inputValue });
    setNModifications(nModifications + 1);

    const isEmpty = !inputValue.trim();
    const isTooShort =
      inputValue.trim().length > 0 && inputValue.trim().length < 4;

    if (nModifications + 1 >= 4) {
      if (isTooShort) {
        setExpNameError(true);
        setExpNameOk(false);
      } else if (isEmpty) {
        setExpNameError(false);
        setExpNameOk(false);
      } else {
        setExpNameError(false);
        setExpNameOk(true);
      }
    } else {
      setExpNameOk(!isEmpty);
    }
  };

  const getNameError = () => {
    const currentName = (
      typeof newExp.name === "string" ? newExp.name : ""
    ).trim();

    if (!currentName && defaultExperimentName && nModifications === 0) {
      return null;
    }

    if (!currentName) {
      return "Name is required";
    }

    const nameExists = existingExperiments.some(
      (experiment) =>
        experiment.name &&
        experiment.name.toLowerCase() === currentName.toLowerCase(),
    );
    if (nameExists) {
      return "An experiment with this name already exists";
    }

    if (expNameError) {
      return "The experiment name must have at least 4 alphanumeric characters.";
    }
    return null;
  };

  const nameError = getNameError();

  useEffect(() => {
    if (selectedTask && "name" in selectedTask) {
      setNewExp({
        ...newExp,
        task_name: selectedTask.name,
        runs: [],
      });
      setTaskNameOk(true);
    }
  }, [selectedTask]);

  useEffect(() => {
    if (defaultExperimentName && !newExp?.name) {
      setNewExp((prev) => ({ ...prev, name: defaultExperimentName }));
      setExpNameOk(true);
    }
  }, [defaultExperimentName]);

  useEffect(() => {
    getTasks();
  }, []);

  useEffect(() => {
    if (expNameOk && taskNameOk) {
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [expNameOk, taskNameOk]);

  return (
    <Grid
      container
      direction="row"
      justifyContent="space-around"
      alignItems="stretch"
      spacing={2}
    >
      {/* Set Name subcomponent */}
      <Grid size={{ xs: 12 }}>
        <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
          Enter a name and select the task for the new experiment
        </Typography>

        <TextField
          id="experiment-name-input"
          label="Experiment name"
          value={newExp.name}
          fullWidth
          onChange={handleNameInputChange}
          sx={{ mb: 2 }}
          error={Boolean(nameError)}
          helperText={nameError}
          slotProps={{
            inputLabel: { shrink: true },
          }}
        />
      </Grid>
      {/* Tasks Subcomponent */}
      <Grid size={{ xs: 12 }}>
        <Grid>
          {/* Tasks list and description */}
          {!loading ? (
            <ItemSelectorWithInfo
              itemsList={tasks}
              selectedItem={selectedTask}
              setSelectedItem={setSelectedTask}
            />
          ) : (
            <CircularProgress color="inherit" />
          )}
        </Grid>
      </Grid>
    </Grid>
  );
}

SetNameAndTaskStep.propTypes = {
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
  defaultExperimentName: PropTypes.string,
  existingExperiments: PropTypes.array,
};

export default SetNameAndTaskStep;
