import PropTypes from "prop-types";
import { Grid, TextField, Typography } from "@mui/material";
import DatasetAutocomplete from "../notebooks/notebookCreation/DatasetAutocomplete";

function SetNameAndDatasetStep({
  formik,
  selectedDataset,
  setSelectedDataset,
  datasets,
  nameError,
  selectedTask,
}) {
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
          name="name"
          variant="outlined"
          fullWidth
          value={formik.values.name}
          onChange={formik.handleChange}
          error={Boolean(nameError)}
          helperText={nameError}
          slotProps={{
            inputLabel: { shrink: true },
          }}
        />
      </Grid>
    </Grid>
  );
}

SetNameAndDatasetStep.propTypes = {
  formik: PropTypes.object.isRequired,
  selectedDataset: PropTypes.object,
  setSelectedDataset: PropTypes.func.isRequired,
  datasets: PropTypes.array.isRequired,
  nameError: PropTypes.string,
  selectedTask: PropTypes.object,
};

export default SetNameAndDatasetStep;
