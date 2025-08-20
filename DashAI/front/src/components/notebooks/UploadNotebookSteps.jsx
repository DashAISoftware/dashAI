import React, { useState } from "react";
import { Typography, TextField, Button, Box } from "@mui/material";
import { useFormik } from "formik";
import CustomLayout from "../custom/CustomLayout";
import DatasetAutocomplete from "./DatasetAutocomplete";
import { createNotebook } from "../../api/notebook";
import { useSnackbar } from "notistack";

export default function UploadNotebookSteps({
  backHome,
  datasets,
  handleNotebookCreated,
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
        const notebookData = {
          name: values.name,
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
  return (
    <CustomLayout title={"Create a New Notebook"} subtitle={""} padding={0}>
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
        label="Notebook Name"
        name="name"
        value={formik.values.name}
        onChange={formik.handleChange}
        error={Boolean(formik.errors.name)}
        helperText={formik.errors.name}
        sx={{ mb: 2 }}
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
      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1 }}>
        <Button variant="outlined" onClick={backHome} sx={{ mr: 1 }}>
          Back
        </Button>
        <Button
          variant="contained"
          disabled={!selectedDataset}
          onClick={formik.handleSubmit}
        >
          Create Notebook
        </Button>
      </Box>
    </CustomLayout>
  );
}
