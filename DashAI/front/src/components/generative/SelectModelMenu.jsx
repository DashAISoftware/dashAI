import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
} from "@mui/material";
import { useFormik } from "formik";
import FormSchemaRenderFields from "../../components/shared/FormSchemaRenderFields";
import { getRelatedComponents } from "../../api/generativeTask";

export default function SelectModelMenu({ selectedTaskName }) {
  const [relatedComponents, setRelatedComponents] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);

  useEffect(() => {
    if (!selectedTaskName) return;

    getRelatedComponents(selectedTaskName).then(setRelatedComponents);
  }, [selectedTaskName]);

  const formik = useFormik({
    initialValues: {},
    onSubmit: (values) => {
      console.log("Form submitted with values:", values);
    },
  });

  useEffect(() => {
    if (selectedModel?.schema?.properties) {
      const initialValues = Object.keys(selectedModel.schema.properties).reduce(
        (acc, key) => {
          acc[key] = selectedModel.schema.properties[key].placeholder || "";
          return acc;
        },
        {},
      );
      formik.setValues(initialValues);
    }
  }, [selectedModel]);

  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
    >
      <Typography
        sx={{
          fontSize: "16px",
          whiteSpace: "normal",
          wordBreak: "break-word",
          ml: 5,
          mt: 1,
          mr: 5,
          mb: 5,
        }}
      >
        Select a model
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
        sx={{ mr: 5, ml: 5, mb: 5 }}
        renderInput={(params) => <TextField {...params} label="Model" />}
      />
      {selectedModel && selectedModel.schema && (
        <form onSubmit={formik.handleSubmit}>
          <Box sx={{ mr: 5, ml: 5, mb: 5 }}>
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
              modelSchema={selectedModel.schema.properties}
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
            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                mt: 2,
              }}
            >
              <Button type="submit" variant="contained">
                Submit
              </Button>
            </Box>
          </Box>
        </form>
      )}
    </Box>
  );
}
