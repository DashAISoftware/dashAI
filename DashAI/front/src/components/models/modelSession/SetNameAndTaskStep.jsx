import { useState, useEffect } from "react";
import PropTypes from "prop-types";

import { CircularProgress, Grid, TextField, Typography } from "@mui/material";
import { useSnackbar } from "notistack";

import { getComponents as getComponentsRequest } from "../../api/component";

import ItemSelectorWithInfo from "../custom/ItemSelectorWithInfo";

import { useTourContext } from "../tour/TourProvider";
import { useTranslation } from "react-i18next";

const EMPTY_ARRAY = [];

function SetNameAndTaskStep({
  newExp,
  setNewExp,
  setNextEnabled,
  defaultExperimentName,
  existingExperiments = EMPTY_ARRAY,
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [loading, setLoading] = useState(false);
  const [nModifications, setNModifications] = useState(0);
  const [expNameError, setExpNameError] = useState(false);
  const tourContext = useTourContext();
  const { t } = useTranslation(["experiments", "common"]);
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState({});

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
      enqueueSnackbar(t("experiments:error.errorFetchingTaskList"), {
        variant: "error",
      });
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
    const nextModifications = nModifications + 1;
    setNewExp({ ...newExp, name: inputValue });
    setNModifications(nextModifications);

    const isEmpty = !inputValue.trim();
    const isTooShort =
      inputValue.trim().length > 0 && inputValue.trim().length < 4;
    const nameExists = existingExperiments.some(
      (experiment) =>
        experiment.name &&
        experiment.name.toLowerCase() === inputValue.trim().toLowerCase(),
    );

    if (nextModifications >= 4) {
      setExpNameError(isTooShort);
    } else {
      setExpNameError(false);
    }

    setNextEnabled(
      Boolean(selectedTask?.name) && !isEmpty && !isTooShort && !nameExists,
    );
  };

  const getNameError = () => {
    const currentName = (
      typeof newExp.name === "string" ? newExp.name : ""
    ).trim();

    if (!currentName && defaultExperimentName && nModifications === 0) {
      return null;
    }

    if (!currentName) {
      return t("experiments:error.nameIsRequired");
    }

    const nameExists = existingExperiments.some(
      (experiment) =>
        experiment.name &&
        experiment.name.toLowerCase() === currentName.toLowerCase(),
    );
    if (nameExists) {
      return t("experiments:error.nameAlreadyExists");
    }

    if (expNameError) {
      return t("experiments:error.nameTooShort");
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
      setNextEnabled(Boolean(selectedTask.name) && !getNameError());

      if (tourContext && tourContext.run) {
        if (selectedTask.name === "TabularClassificationTask") {
          setTimeout(() => {
            tourContext.nextStep();
          }, 300);
        }
      }
    }
  }, [selectedTask]);

  useEffect(() => {
    if (tourContext && tourContext.run) {
      setNewExp((prev) => ({
        ...prev,
        name: "Exp actividad 2",
      }));
      setNextEnabled(Boolean(selectedTask?.name) && !getNameError());
    } else if (defaultExperimentName && !newExp?.name) {
      setNewExp((prev) => ({ ...prev, name: defaultExperimentName }));
      setNextEnabled(Boolean(selectedTask?.name) && !getNameError());
    }
  }, [defaultExperimentName]);

  useEffect(() => {
    getTasks();
  }, []);

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
          {t("experiments:label.setNameAndTask")}
        </Typography>

        <TextField
          id="experiment-name-input"
          data-tour="experiment-name-input"
          label={t("experiments:label.experimentName")}
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
      <Grid size={{ xs: 12 }} data-tour="exp-task-selector">
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
  defaultExperimentName: PropTypes.string,
  existingExperiments: PropTypes.array,
};

export default SetNameAndTaskStep;
