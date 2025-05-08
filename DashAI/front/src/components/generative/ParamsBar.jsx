import React, { useEffect, useState } from "react";
import { Box, Typography, Button } from "@mui/material";
import { useFormik } from "formik";
import FormSchemaRenderFields from "../shared/FormSchemaRenderFields";
import {
  getGenerativeSession,
  getRelatedComponents,
  updateGenerativeSessionParams,
} from "../../api/generativeTask";

export default function ParamsBar({ selectedSessionId, onParamsUpdate }) {
  const [parameters, setParameters] = useState({});
  const [schema, setSchema] = useState(null);

  useEffect(() => {
    if (!selectedSessionId) return;

    getGenerativeSession(selectedSessionId)
      .then((session) => {
        setParameters(session.parameters);

        getRelatedComponents(session.task_name).then((relatedComponents) => {
          const relatedModel = relatedComponents.find(
            (component) => component.name === session.model_name,
          );

          if (relatedModel && relatedModel.schema) {
            const modelSchema = relatedModel.schema.properties;
            const combinedSchema = Object.keys(modelSchema).reduce(
              (acc, key) => {
                acc[key] = {
                  ...modelSchema[key],
                  title: key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (char) => char.toUpperCase()),
                  placeholder:
                    session.parameters[key] || modelSchema[key].default || "",
                };
                return acc;
              },
              {},
            );

            setSchema({ properties: combinedSchema });
          }
        });
      })
      .catch((error) => console.error("Error fetching session data:", error));
  }, [selectedSessionId]);

  const handleUpdateParameters = async (updatedParams) => {
    try {
      const updatedSession = await updateGenerativeSessionParams(
        selectedSessionId,
        updatedParams,
      );
      setParameters(updatedSession.parameters);
      onParamsUpdate(updatedSession.parameters);
    } catch (error) {
      console.error("Failed to update session parameters:", error);
    }
  };

  const formik = useFormik({
    initialValues: parameters,
    enableReinitialize: true,
    onSubmit: (values) => handleUpdateParameters(values),
  });

  if (!schema) return null;

  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"auto"}
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
        Edit Parameters
      </Typography>
      <form onSubmit={formik.handleSubmit}>
        <Box sx={{ mr: 5, ml: 5, mb: 5 }}>
          {/* Render the parameter fields */}
          <FormSchemaRenderFields
            modelSchema={schema.properties}
            formik={{
              values: formik.values,
              setFieldValue: formik.setFieldValue,
              handleSubmit: formik.handleSubmit,
              errors: formik.errors || {},
            }}
            autoSave={false}
            handleUpdateSchema={(updatedValues) => {
              formik.setValues((prevValues) => ({
                ...prevValues,
                ...updatedValues,
              }));
            }}
            onFormSubmit={formik.handleSubmit}
            setError={(error) => console.error(error)}
            errorsMessage={formik.errors || {}}
          />
          <Box
            sx={{
              display: "flex",
              justifyContent: "flex-end",
              mt: 2,
            }}
          >
            <Button type="submit" variant="contained" disabled={!formik.dirty}>
              EDIT
            </Button>
          </Box>
        </Box>
      </form>
    </Box>
  );
}
