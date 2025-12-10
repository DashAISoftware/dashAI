import { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { Grid, TextField, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import ItemSelectorWithInfo from "../custom/ItemSelectorWithInfo";

function SetNameAndDatasetStep({
  sessionName,
  setSessionName,
  selectedDataset,
  setSelectedDataset,
  datasets,
  setNextEnabled,
  existingSessions = [],
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [nModifications, setNModifications] = useState(0);
  const [nameOk, setNameOk] = useState(false);
  const [nameError, setNameError] = useState(false);
  const [datasetOk, setDatasetOk] = useState(false);

  const handleNameInputChange = (event) => {
    const inputValue = event.target.value;
    setSessionName(inputValue);
    setNModifications(nModifications + 1);

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
        <Typography variant="h6" gutterBottom>
          Set Session Name and Select Dataset
        </Typography>
      </Grid>

      <Grid item>
        <TextField
          id="session-name"
          label="Session Name"
          variant="outlined"
          fullWidth
          value={sessionName || ""}
          onChange={handleNameInputChange}
          error={Boolean(displayNameError)}
          helperText={displayNameError}
          required
        />
      </Grid>

      <Grid item sx={{ flexGrow: 1, minHeight: 0 }}>
        <ItemSelectorWithInfo
          itemsList={datasets.map((dataset) => ({
            name: dataset.name,
            description: dataset.description || "No description",
          }))}
          setSelectedItem={(datasetItem) => {
            const dataset = datasets.find((d) => d.name === datasetItem.name);
            setSelectedDataset(dataset);
          }}
          selectedItem={
            selectedDataset
              ? {
                  name: selectedDataset.name,
                  description: selectedDataset.description || "No description",
                }
              : {}
          }
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
};

export default SetNameAndDatasetStep;
