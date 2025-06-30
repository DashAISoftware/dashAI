import { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
  IconButton,
} from "@mui/material";
import { useFormik } from "formik";
import FormSchemaRenderFields from "../../components/shared/FormSchemaRenderFields";
import { getRelatedComponents } from "../../api/generativeTask";
import { createGenerativeSession } from "../../api/generativeTask";
import { preprocessSchema, buildYupSchema } from "./utils";

export default function SelectModelMenu({
  goToBackStep,
  selectedTaskName,
  setSelectedSessionId,
  handleAddSession,
}) {
  const [relatedComponents, setRelatedComponents] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [validationSchema, setValidationSchema] = useState(null);

  useEffect(() => {
    if (!selectedTaskName) return;

    getRelatedComponents(selectedTaskName).then(setRelatedComponents);
  }, [selectedTaskName]);

  useEffect(() => {
    if (selectedModel?.schema?.properties) {
      // Preprocess the schema properties to ensure they are in the correct format
      const processedProps = preprocessSchema(selectedModel.schema.properties);

      setValidationSchema(buildYupSchema(processedProps));
      const initialValues = Object.keys(processedProps).reduce(
        (acc, key) => {
          acc[key] = processedProps[key].placeholder || "";
          return acc;
        },
        { name: "", description: "" },
      );
      formik.setValues(initialValues);
    }
  }, [selectedModel]);

  const formik = useFormik({
    initialValues: {
      name: "",
      description: "",
    },
    validationSchema,
    enableReinitialize: true,
    onSubmit: async (values) => {
      try {
        const sessionData = {
          name: values.name,
          description: values.description,
          task_name: selectedTaskName,
          model_name: selectedModel?.name || "",
          parameters: values,
        };

        const createdSession = await createGenerativeSession(sessionData);

        setSelectedSessionId(createdSession.id);
        handleAddSession(createdSession);
      } catch (error) {
        console.error("Error creating session:", error);
      }
    },
  });

  const processedProperties = selectedModel?.schema?.properties
    ? preprocessSchema(selectedModel.schema.properties)
    : {};

  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"auto"}
      pl={5}
      pr={5}
    >
      <Typography
        variant="h5"
        component="h2"
        sx={{
          whiteSpace: "normal",
          wordBreak: "break-word",
          mt: 2,
          mb: 4,
        }}
      >
        {selectedTaskName}: Select a model and configure parameters
      </Typography>
      <Autocomplete
        disablePortal
        options={relatedComponents.map((t) => t.name)}
        onChange={(event, newValue) => {
          const selected = relatedComponents.find(
            (model) => model.name === newValue,
          );
          setSelectedModel(selected);
        }}
        sx={{ mb: 5 }}
        renderInput={(params) => <TextField {...params} label="Model" />}
      />
      {!selectedModel && (
        <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 1 }}>
          <Button variant="outlined" onClick={goToBackStep} sx={{ mr: 1 }}>
            Back to Task Selection
          </Button>
          <Button variant="contained" disabled>
            Create a session
          </Button>
        </Box>
      )}

      {selectedModel && selectedModel.schema && (
        <form onSubmit={formik.handleSubmit}>
          <Box sx={{ mb: 5 }}>
            <Box width="60%">
              <Typography
                sx={{
                  fontSize: "16px",
                  whiteSpace: "normal",
                  wordBreak: "break-word",
                  mb: 2,
                }}
              >
                Parameters
              </Typography>
              <FormSchemaRenderFields
                modelSchema={processedProperties}
                formik={formik}
                autoSave={false}
                handleUpdateSchema={(updatedValues) => {
                  formik.setValues((prevValues) => ({
                    ...prevValues,
                    ...updatedValues,
                  }));
                }}
                onFormSubmit={formik.handleSubmit}
                setError={(error) => console.error(error)}
                errorsMessage={formik.errors}
              />
            </Box>
            <Typography
              sx={{
                fontSize: "16px",
                whiteSpace: "normal",
                wordBreak: "break-word",
                mb: 2,
              }}
            >
              Name your session
            </Typography>
            {/* Session name */}
            <TextField
              fullWidth
              label="Session Name"
              name="name"
              value={formik.values.name}
              onChange={formik.handleChange}
              error={Boolean(formik.errors.name)}
              helperText={formik.errors.name}
              sx={{ mb: 2 }}
            />
            {/* Session description */}
            <TextField
              fullWidth
              label="Session Description"
              name="description"
              value={formik.values.description}
              onChange={formik.handleChange}
              error={Boolean(formik.errors.description)}
              helperText={formik.errors.description}
              sx={{ mb: 2 }}
            />

            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                mt: 2,
              }}
            >
              <Button variant="outlined" onClick={goToBackStep} sx={{ mr: 1 }}>
                Back to Task Selection
              </Button>
              <Button type="submit" variant="contained">
                Create a session
              </Button>
            </Box>
          </Box>
        </form>
      )}
    </Box>
  );
}
