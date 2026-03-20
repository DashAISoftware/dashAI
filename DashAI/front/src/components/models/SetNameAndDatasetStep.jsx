import PropTypes from "prop-types";
import { Grid, TextField, Typography } from "@mui/material";
import DatasetAutocomplete from "../notebooks/notebookCreation/DatasetAutocomplete";
import { useTranslation } from "react-i18next";

function SetNameAndDatasetStep({
  formik,
  selectedDataset,
  setSelectedDataset,
  datasets,
  nameError,
  selectedTask,
  onDatasetChange,
}) {
  const { t } = useTranslation(["models"]);
  const handleDatasetChange = (newDataset) => {
    setSelectedDataset(newDataset);
    if (onDatasetChange) {
      onDatasetChange(newDataset);
    }
  };

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
      <Grid>
        <Typography
          variant="h6"
          sx={{
            whiteSpace: "normal",
            wordBreak: "break-word",
            mb: 2,
          }}
        >
          {t("models:label.selectDatasetForSession")}
        </Typography>
        <DatasetAutocomplete
          datasets={datasets}
          selectedDataset={selectedDataset}
          setSelectedDataset={handleDatasetChange}
        />
      </Grid>

      <Grid>
        <Typography
          variant="h6"
          sx={{
            whiteSpace: "normal",
            wordBreak: "break-word",
            my: 2,
          }}
        >
          {t("models:label.nameYourSession")}
        </Typography>
        <TextField
          id="session-name"
          label={t("models:label.sessionName")}
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
  onDatasetChange: PropTypes.func,
};

export default SetNameAndDatasetStep;
