import { useEffect, useState } from "react";
import { Box, Typography, Button, IconButton } from "@mui/material";
import { useFormik } from "formik";
import FormSchemaRenderFields from "../shared/FormSchemaRenderFields";
import HistoryIcon from "@mui/icons-material/History";
import ParameterHistoryModal from "./SessionHistoryModal";
import { getHistoryBySessionId } from "../../api/session";
import {
  getGenerativeSession,
  getRelatedComponents,
  updateGenerativeSessionParams,
} from "../../api/generativeTask";
import { preprocessSchema, buildYupSchema } from "./utils"; 

export default function ParamsBar({
  selectedSessionId,
  onParamsUpdate,
  taskName,
}) {
  const [parameters, setParameters] = useState({});
  const [historyInfoVisible, setHistoryInfoVisible] = useState(false);
  const [history, setHistory] = useState([]);
  const [schema, setSchema] = useState(null);
  const [validationSchema, setValidationSchema] = useState(null);

  const getHistory = () => {
    getHistoryBySessionId(selectedSessionId).then((response) => {
      setHistory(response);
    });
  };

  useEffect(() => {
    if (!selectedSessionId) return;
    getHistory();
  }, []);

  useEffect(() => {
    if (!selectedSessionId) return;

    getGenerativeSession(selectedSessionId)
      .then((session) => {
        setParameters(session.parameters);
        console.log("Session task name:", session.task_name);
        getRelatedComponents(session.task_name).then((relatedComponents) => {
          const relatedModel = relatedComponents.find(
            (component) => component.name === session.model_name,
          );

          if (relatedModel && relatedModel.schema) {
            const modelSchema = preprocessSchema(relatedModel.schema.properties);
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
            setValidationSchema(buildYupSchema(combinedSchema));
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
    validationSchema,
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
      bgcolor={"background.box"}
      borderRadius={2}
    >
      <Box
        display={"flex"}
        justifyContent={"space-between"}
        alignItems={"center"}
        p="40px"
        pt="30px"
      >
        <Typography
          sx={{
            fontSize: "16px",
            whiteSpace: "normal",
            wordBreak: "break-word",
          }}
        >
          Edit Parameters
        </Typography>

        {/* Parameter History Modal */}
        <IconButton
          onClick={() => {
            getHistory();
            setHistoryInfoVisible(true);
          }}
        >
          <HistoryIcon
            sx={{
              color: "#a0a0a0",
              "&:hover": {
                color: "#ffffff",
              },
            }}
          />
        </IconButton>
      </Box>
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
            spacing={0}
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

      {/* Parameter History Modal */}
      <ParameterHistoryModal
        historyChanges={history}
        open={historyInfoVisible}
        taskName={taskName}
        setOpen={setHistoryInfoVisible}
      />
    </Box>
  );
}
