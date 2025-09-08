import { useState, useMemo } from "react";
import { Typography, TextField, Box } from "@mui/material";
import { useFormik } from "formik";
import CustomLayout from "../../custom/CustomLayout";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import DatasetAutocomplete from "./DatasetAutocomplete";
import { createNotebook } from "../../../api/notebook";
import { useSnackbar } from "notistack";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import NoteBox from "../NoteBox";
import { generateNotebookName } from "../../../utils/notebookNameGenerator";

export default function UploadNotebookSteps({
  backHome,
  datasets,
  handleNotebookCreated,
  existingNotebooks = [],
}) {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const { enqueueSnackbar } = useSnackbar();

  const { defaultName, placeholderName } = useMemo(
    () => generateNotebookName(selectedDataset, existingNotebooks),
    [selectedDataset, existingNotebooks],
  );

  const formik = useFormik({
    initialValues: {
      name: "",
      description: "",
    },
    enableReinitialize: true,
    onSubmit: async (values) => {
      try {
        const notebookName = values.name.trim() || defaultName;

        if (existingNotebooks.some((nb) => nb.name === notebookName)) {
          enqueueSnackbar("A notebook with this name already exists", {
            variant: "warning",
          });
          return;
        }

        const notebookData = {
          name: notebookName,
          description: values.description,
          dataset_id: selectedDataset.id,
        };

        const createdNotebook = await createNotebook(notebookData);

        enqueueSnackbar("Notebook created successfully", {
          variant: "success",
        });
        handleNotebookCreated(createdNotebook);
      } catch (error) {
        console.error("Error creating notebook:", error);

        if (error.response?.status === 409) {
          enqueueSnackbar("Notebook name already exists", { variant: "error" });
        } else {
          enqueueSnackbar("Error creating notebook", { variant: "error" });
        }
      }
    },
  });

  return (
    <CustomLayout title={"Create a New Notebook"} subtitle={""} padding={0}>
      <NoteBox message="A copy of the selected dataset will be created to work in the notebook without altering the original." />
      <Typography
        variant="h6"
        sx={{
          whiteSpace: "normal",
          wordBreak: "break-word",
          mb: 2,
        }}
      >
        Select dataset for your notebook
      </Typography>
      <DatasetAutocomplete
        datasets={datasets}
        selectedDataset={selectedDataset}
        setSelectedDataset={setSelectedDataset}
      />
      <Typography
        variant="h6"
        sx={{
          whiteSpace: "normal",
          wordBreak: "break-word",
          my: 2,
        }}
      >
        Name your Notebook
      </Typography>
      {/* Notebook name */}
      <TextField
        fullWidth
        label="Notebook Name (optional)"
        name="name"
        value={formik.values.name}
        onChange={formik.handleChange}
        placeholder={placeholderName}
        InputLabelProps={{ shrink: true }}
        error={Boolean(formik.errors.name)}
        helperText={formik.errors.name}
        sx={{ mb: 2 }}
        key={selectedDataset?.id}
      />
      {/* Notebook description */}
      <TextField
        fullWidth
        label="Notebook Description"
        name="description"
        value={formik.values.description}
        onChange={formik.handleChange}
        error={Boolean(formik.errors.description)}
        helperText={formik.errors.description}
        sx={{ mb: 2 }}
      />
      <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
        <FormSchemaButtonGroup
          onCancel={backHome}
          onFormSubmit={formik.handleSubmit}
          formik={{
            errors: selectedDataset ? {} : { dataset: "Dataset is required" },
          }}
          saveButtonText="Create Notebook"
          backButtonText="Back"
        />
      </Box>
    </CustomLayout>
  );
}
