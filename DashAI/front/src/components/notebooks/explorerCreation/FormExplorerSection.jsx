import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";

import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useSnackbar } from "notistack";
import ParameterStepExplorer from "./ParameterStepExplorer";
import ScopeStepExplorer from "./ScopeStepExplorer";
import { createNotebookExplorer } from "../../../api/explorer";
import { enqueueExplorerJob, startJobQueue } from "../../../api/job";

export default function FormExplorerSection({
  step,
  setStep,
  handleClose,
  tool,
  notebook,
}) {
  const [classColumnInitialValue, setClassColumnInitialValue] = useState(null);
  const [scopeColumns, setScopeColumns] = useState([]);
  const [formValues, setFormValues] = useState({
    notebook_id: notebook.id,
    explorer: tool.name,
    parameters: {
      params: {},
      scope: {
        columns: [],
        rows: [],
      },
      order: 1,
      target_index: null,
    },
  });

  const { explorersAndConverters, setExplorersAndConverters } =
    useExplorersAndConverters();
  const { enqueueSnackbar } = useSnackbar();

  const handleSaveExplorer = async (params) => {
    // Build columns as expected by backend (list of objects with at least columnName)
    const selectedColumns = scopeColumns.map((c) => ({
      columnName: c.columnName,
      // keep any available metadata if present
      ...(c.valueType ? { valueType: c.valueType } : {}),
      ...(c.dataType ? { dataType: c.dataType } : {}),
      ...(c.id !== undefined ? { id: c.id } : {}),
      ...(c.order !== undefined ? { order: c.order } : {}),
    }));

    createNotebookExplorer(notebook.id, selectedColumns, tool.name, params)
      .then((created) => {
        const data = { ...created, type: "explorer" };
        setExplorersAndConverters((prev) => [...prev, data]);
        enqueueSnackbar(`Explorer ${tool.name} created successfully`, {
          variant: "success",
        });
        enqueueExplorerJob(created.id)
          .then(() => {
            startJobQueue();
          })
          .catch((error) => {
            console.error("Error enqueuing explorer job:", error);
          });
      })
      .catch((error) => {
        console.error("Error creating explorer:", error);
        enqueueSnackbar("Failed to create explorer", { variant: "error" });
      })
      .finally(() => {
        handleClose();
      });
  };

  useEffect(() => {
    const copyValues = structuredClone(formValues);
    copyValues.parameters.target_index = classColumnInitialValue;
    copyValues.parameters.scope.columns = scopeColumns.map((c) => c.columnName);
    setFormValues(copyValues);
  }, [classColumnInitialValue, scopeColumns]);

  return (
    <Box
      sx={{
        overflow: "auto",
        display: "flex",
        flexDirection: "column",
        flexGrow: 1,
      }}
    >
      {/* Step content */}
      {step === 0 && (
        <ScopeStepExplorer
          classColumnInitialValue={classColumnInitialValue}
          setClassColumnInitialValue={setClassColumnInitialValue}
          notebook={notebook}
          tool={tool}
          setScopeColumns={setScopeColumns}
          nextStep={
            Object.values(tool.schema.properties).length > 0
              ? () => setStep((s) => s + 1)
              : () => handleSaveExplorer({})
          }
        />
      )}

      {step === 1 && (
        <ParameterStepExplorer
          explorer={tool.name}
          initialParams={{}}
          handleSaveExplorer={handleSaveExplorer}
          setStep={setStep}
        />
      )}
    </Box>
  );
}
