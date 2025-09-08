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
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [loading, setLoading] = useState(false);
  const [nModifications, setNModifications] = useState(0);
  const [expNameOk, setExpNameOk] = useState(true);
  const [expNameError, setExpNameError] = useState(false);

  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState({});
  const [taskNameOk, setTaskNameOk] = useState(false);

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

    if (nModifications + 1 >= 4) {
      if (inputValue.trim().length > 0 && inputValue.trim().length < 4) {
        setExpNameError(true);
        setExpNameOk(false);
      } else {
        setExpNameError(false);
        setExpNameOk(true);
      }
    }
  };

  // when a task is selected it synchronizes the value of the selected task (object) with the value in newExp (string)
  useEffect(() => {
    if (selectedTask && "name" in selectedTask) {
      setNewExp({
        ...newExp,
        task_name: selectedTask.name,
        dataset: null,
        runs: [],
      });
      setTaskNameOk(true);
    }
  }, [selectedTask]);

  // on mount, fetch tasks.
  useEffect(() => {
    getTasks();
  }, []);

  // enable next button y nameOk and taskOk are true.
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
      <Grid item xs={12}>
        <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
          Enter a name and select the task for the new experiment
        </Typography>

        <TextField
          id="experiment-name-input"
          label="Experiment name (optional)"
          value={newExp.name}
          fullWidth
          onChange={handleNameInputChange}
          placeholder={defaultExperimentName}
          InputLabelProps={{ shrink: true }}
          sx={{ mb: 2 }}
          error={expNameError}
          helperText="The experiment name must have at least 4 alphanumeric characters."
        />
      </Grid>

      {/* Tasks Subcomponent */}
      <Grid item xs={12}>
        <Grid container spacing={1}>
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
};

export default SetNameAndTaskStep;
