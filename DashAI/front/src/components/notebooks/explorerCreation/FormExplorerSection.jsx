import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useSnackbar } from "notistack";
import ParameterStepExplorer from "./ParameterStepExplorer";
import ScopeStepExplorer from "./ScopeStepExplorer";
import { createNotebookExplorer } from "../../../api/explorer";
import { enqueueExplorerJob } from "../../../api/job";
import { startJobPolling } from "../../../utils/jobPoller";
import { useTranslation } from "react-i18next";

export default function FormExplorerSection({
  step,
  setStep,
  handleClose,
  tool,
  notebook,
  hideButtons = false,
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

  const {
    explorersAndConverters,
    setExplorersAndConverters,
    setLastAddedItemId,
  } = useExplorersAndConverters();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);

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
      setLastAddedItemId(data.id);

      const response = await enqueueExplorerJob(created.id);

      if (response && response.id) {
        const jobId = response.id;

        startJobPolling(
          jobId,
          (result) => {
            enqueueSnackbar(
              t("datasets:message.explorerProcessedSuccessfully", {
                name: tool.name,
              }),
              {
                variant: "success",
              },
            );
          },
          (result) => {
            enqueueSnackbar(
              t("datasets:error.errorProcessingExplorer", {
                error: result.error || t("common:unknownError"),
              }),
              { variant: "error" },
            );
          },
        );
      }
      handleClose();
    } catch (error) {
      console.error("Error creating explorer:", error);
      enqueueSnackbar(t("datasets:error.failedToCreateExplorer"), {
        variant: "error",
      });
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
        flex: 1,
        maxHeight: "100%",
        minHeight: 0,
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
          hideButtons={hideButtons}
        />
      )}

      {step === 1 && (
        <ParameterStepExplorer
          explorer={tool.name}
          initialParams={{}}
          handleSaveExplorer={handleSaveExplorer}
          setStep={setStep}
          hideButtons={hideButtons}
        />
      )}
    </Box>
  );
}
