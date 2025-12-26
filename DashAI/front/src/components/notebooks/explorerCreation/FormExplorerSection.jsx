import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useSnackbar } from "notistack";
import ParameterStepExplorer from "./ParameterStepExplorer";
import ScopeStepExplorer from "./ScopeStepExplorer";
import { createNotebookExplorer } from "../../../api/explorer";
import { enqueueExplorerJob } from "../../../api/job";
import { startJobPolling } from "../../../utils/jobPoller";

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
    try {
      const selectedColumns = scopeColumns.map((c) => ({
        columnName: c.columnName,
        ...(c.valueType ? { valueType: c.valueType } : {}),
        ...(c.dataType ? { dataType: c.dataType } : {}),
        ...(c.id !== undefined ? { id: c.id } : {}),
        ...(c.order !== undefined ? { order: c.order } : {}),
      }));
      const created = await createNotebookExplorer(
        notebook.id,
        selectedColumns,
        tool.name,
        params,
      );
      const data = { ...created, type: "explorer" };
      setExplorersAndConverters((prev) => [...prev, data]);

      const response = await enqueueExplorerJob(created.id);

      if (response && response.id) {
        const jobId = response.id;

        startJobPolling(
          jobId,
          (result) => {
            enqueueSnackbar(`Explorer ${tool.name} processed successfully`, {
              variant: "success",
            });
          },
          (result) => {
            enqueueSnackbar(
              `Error processing explorer: ${result.error || "Unknown error"}`,
              { variant: "error" },
            );
          },
        );
      }
      handleClose();
    } catch (error) {
      console.error("Error creating explorer:", error);
      enqueueSnackbar("Failed to create explorer", { variant: "error" });
    }
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
        overflow: "visible",
        display: "flex",
        flexDirection: "column",
        flexGrow: 1,
        maxHeight: "100%",
      }}
    >
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
