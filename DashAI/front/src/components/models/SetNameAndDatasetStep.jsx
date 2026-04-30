import PropTypes from "prop-types";
import { Box, TextField } from "@mui/material";
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
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <DatasetAutocomplete
        datasets={datasets}
        selectedDataset={selectedDataset}
        setSelectedDataset={handleDatasetChange}
      />
      <TextField
        id="session-name"
        label={t("models:label.sessionName")}
        name="name"
        variant="outlined"
        fullWidth
        value={formik.values.name}
        onChange={formik.handleChange}
        onBlur={formik.handleBlur}
        error={Boolean(nameError)}
        helperText={nameError}
        disabled={!selectedDataset}
        placeholder={
          !selectedDataset
            ? t("models:label.selectDatasetFirst", {
                defaultValue: "Select a dataset first",
              })
            : t("models:label.sessionName")
        }
      />
    </Box>
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
