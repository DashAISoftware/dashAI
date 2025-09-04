import { useState } from "react";
import { Typography, TextField, Box } from "@mui/material";
import { useFormik } from "formik";
import CustomLayout from "../../custom/CustomLayout";
import DatasetAutocomplete from "./DatasetAutocomplete";
import { createNotebook } from "../../../api/notebook";
import { useSnackbar } from "notistack";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import NoteBox from "../NoteBox";

export default function UploadNotebookSteps({
  backHome,
  datasets,
  handleNotebookCreated,
  existingNotebooks = [], // Add this prop to get existing notebooks
}) {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const { enqueueSnackbar } = useSnackbar();

  const formik = useFormik({
    initialValues: {
      name: "",
      description: "",
    },
    // validationSchema,
    enableReinitialize: true,
    onSubmit: async (values) => {
      try {
        // Generate automatic name similar to ConfigureModelsStep
        let notebookName;
        if (values.name.trim() === "") {
          const baseName = selectedDataset?.name
            ? `Notebook_${selectedDataset.name}`
            : "Notebook";

          // Count existing notebooks with similar names
          const existingNotebooksOfType = existingNotebooks.filter((notebook) =>
            notebook.name.startsWith(baseName),
          ).length;

          notebookName = `${baseName}_${existingNotebooksOfType + 1}`;
        } else {
          notebookName = values.name;
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
        enqueueSnackbar("Error creating notebook", { variant: "error" });
      }
    },
  });

  // Generate placeholder text based on selected dataset and existing notebooks
  const getPlaceholder = () => {
    if (selectedDataset) {
      const baseName = `Notebook_${selectedDataset.name}`;
      const existingNotebooksOfType = existingNotebooks.filter((notebook) =>
        notebook.name.startsWith(baseName),
      ).length;
      return `${baseName}_${existingNotebooksOfType + 1}`;
    }
    return "Notebook_1";
  };

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
        placeholder={getPlaceholder()}
        InputLabelProps={{ shrink: true }}
        error={Boolean(formik.errors.name)}
        helperText={formik.errors.name}
        sx={{ mb: 2 }}
        key={selectedDataset?.id} // Re-render when dataset changes
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
