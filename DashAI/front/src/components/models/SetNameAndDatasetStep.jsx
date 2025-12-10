import { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import { Grid, TextField, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import DatasetAutocomplete from "../notebooks/notebookCreation/DatasetAutocomplete";
import { generateSequentialName } from "../../utils/nameGenerator";

function SetNameAndDatasetStep({
  sessionName,
  setSessionName,
  selectedDataset,
  setSelectedDataset,
  datasets,
  setNextEnabled,
  existingSessions = [],
  selectedTask,
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [nModifications, setNModifications] = useState(0);
  const [nameOk, setNameOk] = useState(false);
  const [nameError, setNameError] = useState(false);
  const [datasetOk, setDatasetOk] = useState(false);
  const [hasUserModifiedName, setHasUserModifiedName] = useState(false);

  const { defaultName } = useMemo(() => {
    if (!selectedTask) {
      return { defaultName: "" };
    }

    const taskDisplayName =
      selectedTask.metadata?.display_name ||
      selectedTask.name
        .replace("Task", "")
        .replace(/([A-Z])/g, " $1")
        .trim();

    return generateSequentialName({
      base: `Session_${taskDisplayName}`,
      items: existingSessions,
      filter: (session) => session.task_name === selectedTask.name,
    });
  }, [selectedTask, existingSessions]);

  useEffect(() => {
    if (
      selectedTask &&
      defaultName &&
      !sessionName.trim() &&
      !hasUserModifiedName
    ) {
      setSessionName(defaultName);
      setNameOk(true);
    }
  }, [
    selectedTask,
    defaultName,
    sessionName,
    setSessionName,
    hasUserModifiedName,
  ]);

  const handleNameInputChange = (event) => {
    const inputValue = event.target.value;
    setSessionName(inputValue);
    setNModifications(nModifications + 1);
    setHasUserModifiedName(true);

    const isEmpty = !inputValue.trim();
    const isTooShort =
      inputValue.trim().length > 0 && inputValue.trim().length < 4;

    if (nModifications + 1 >= 4) {
      if (isTooShort) {
        setNameError(true);
        setNameOk(false);
      } else if (isEmpty) {
        setNameError(false);
        setNameOk(false);
      } else {
        setNameError(false);
        setNameOk(true);
      }
    } else {
      setNameOk(!isEmpty);
    }
  };

  const getNameError = () => {
    const currentName = (
      typeof sessionName === "string" ? sessionName : ""
    ).trim();

    if (!currentName) {
      return "Name is required";
    }

    const nameExists = existingSessions.some(
      (session) =>
        session.name &&
        session.name.toLowerCase() === currentName.toLowerCase(),
    );
    if (nameExists) {
      return "A session with this name already exists";
    }

    if (nameError) {
      return "The session name must have at least 4 alphanumeric characters.";
    }
    return null;
  };

  const displayNameError = getNameError();

  useEffect(() => {
    if (selectedDataset && selectedDataset.id) {
      setDatasetOk(true);
    } else {
      setDatasetOk(false);
    }
  }, [selectedDataset]);

  useEffect(() => {
    setNextEnabled(nameOk && datasetOk && !displayNameError);
  }, [nameOk, datasetOk, displayNameError, setNextEnabled]);

  return (
    <Grid
      container
      spacing={2}
      direction="column"
      sx={{
        height: "100%",
        width: "100%",
        padding: 2,
      }}
    >
      <Grid item>
        <Typography
          variant="h6"
          sx={{
            whiteSpace: "normal",
            wordBreak: "break-word",
            mb: 2,
          }}
        >
          Select dataset for your session
        </Typography>
        <DatasetAutocomplete
          datasets={datasets}
          selectedDataset={selectedDataset}
          setSelectedDataset={setSelectedDataset}
        />
      </Grid>

      <Grid item>
        <Typography
          variant="h6"
          sx={{
            whiteSpace: "normal",
            wordBreak: "break-word",
            my: 2,
          }}
        >
          Name your Session
        </Typography>
        <TextField
          id="session-name"
          label="Session Name"
          variant="outlined"
          fullWidth
          value={sessionName || ""}
          onChange={handleNameInputChange}
          error={Boolean(displayNameError)}
          helperText={displayNameError}
        />
      </Grid>
    </Grid>
  );
}

SetNameAndDatasetStep.propTypes = {
  sessionName: PropTypes.string.isRequired,
  setSessionName: PropTypes.func.isRequired,
  selectedDataset: PropTypes.object,
  setSelectedDataset: PropTypes.func.isRequired,
  datasets: PropTypes.array.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  existingSessions: PropTypes.array,
  selectedTask: PropTypes.object,
};

export default SetNameAndDatasetStep;
