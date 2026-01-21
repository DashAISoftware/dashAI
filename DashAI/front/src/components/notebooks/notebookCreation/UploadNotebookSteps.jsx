import { useState, useMemo, useEffect } from "react";
import { Typography, TextField, Box } from "@mui/material";
import { useFormik } from "formik";
import CustomLayout from "../../custom/CustomLayout";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import DatasetAutocomplete from "./DatasetAutocomplete";
import { createNotebook } from "../../../api/notebook";
import { useSnackbar } from "notistack";
import { generateSequentialName } from "../../../utils/nameGenerator";
import NoteBox from "../NoteBox";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

export default function UploadNotebookSteps({
  backHome,
  datasets,
  handleNotebookCreated,
  existingNotebooks = [],
  preselectedDatasetId = null,
}) {
  const [selectedDataset, setSelectedDataset] = useState(
    preselectedDatasetId
      ? datasets.find((d) => d.id === preselectedDatasetId) || null
      : null,
  );
  const { enqueueSnackbar } = useSnackbar();
  const tourContext = useTourContext();
  const { t } = useTranslation(["datasets", "common"]);

  const { defaultName } = useMemo(() => {
    if (!selectedDataset) {
      return { defaultName: "" };
    }

    return generateSequentialName({
      base: `Notebook_${selectedDataset.name}`,
      items: existingNotebooks,
      filter: (notebook) => notebook.dataset_id === selectedDataset.id,
    });
  }, [selectedDataset, existingNotebooks]);

  const formik = useFormik({
    initialValues: {
      name: "",
      description: "",
    },
    enableReinitialize: true,
    onSubmit: async (values) => {
      try {
        const notebookName = values.name.trim();

        if (!notebookName) {
          return;
        }

        const notebookData = {
          name: notebookName,
          description: values.description,
          dataset_id: selectedDataset.id,
        };

        const createdNotebook = await createNotebook(notebookData);

        enqueueSnackbar(t("datasets:message.notebookCreated"), {
          variant: "success",
        });
        handleNotebookCreated(createdNotebook);
        if (tourContext?.run) {
          tourContext.stopTour();
        }
      } catch (error) {
        console.error("Error creating notebook:", error);
        enqueueSnackbar(t("datasets:error.errorCreatingNotebook"), {
          variant: "error",
        });
      }
    },
  });

  useEffect(() => {
    if (selectedDataset && defaultName && !formik.values.name.trim()) {
      formik.setValues({
        name: defaultName,
        description: formik.values.description,
      });
    }
  }, [
    selectedDataset,
    defaultName,
    formik.values.name,
    formik.values.description,
  ]);

  const getNameError = () => {
    if (!selectedDataset) {
      return null;
    }

    const currentName = formik.values.name.trim();
    if (!currentName) {
      return t("common:nameRequired");
    }
    return null;
  };

  const nameError = getNameError();

  return (
    <CustomLayout
      title={t("datasets:label.createNewNotebook")}
      subtitle={""}
      padding={0}
    >
      <NoteBox message={t("datasets:label.notebookCreationNote")} />
      <Typography
        variant="h6"
        sx={{
          whiteSpace: "normal",
          wordBreak: "break-word",
          mb: 2,
        }}
      >
        {t("datasets:label.selectDatasetForNotebook")}
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
        {t("datasets:label.nameYourNotebook")}
      </Typography>
      {/* Notebook name */}
      <TextField
        fullWidth
        label={t("datasets:label.notebookName")}
        name="name"
        value={formik.values.name}
        onChange={formik.handleChange}
        error={Boolean(selectedDataset && nameError)}
        helperText={selectedDataset ? nameError : ""}
        sx={{ mb: 2 }}
        disabled={!selectedDataset}
        placeholder={
          !selectedDataset
            ? t("datasets:label.selectDatasetFirst")
            : t("datasets:label.notebookName")
        }
        slotProps={{
          inputLabel: { shrink: true },
        }}
      />
      {/* Notebook description */}
      <TextField
        fullWidth
        label={t("datasets:label.notebookDescription")}
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
            errors: {
              ...(nameError ? { name: nameError } : {}),
              ...(selectedDataset
                ? {}
                : { dataset: t("datasets:error.datasetRequired") }),
            },
          }}
          saveButtonText={t("datasets:button.createNotebook")}
          backButtonText={t("common:back")}
        />
      </Box>
    </CustomLayout>
  );
}
