import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";

import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useSnackbar } from "notistack";
import ParameterStepExplorer from "./ParameterStepExplorer";
import ScopeStepExplorer from "./ScopeStepExplorer";

export default function FormExplorerSection({
  step,
  setStep,
  handleClose,
  tool,
  notebook,
}) {
  const [initialParams, setInitialParams] = useState({});
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
    enqueueSnackbar(`Explorer ${tool.name} configured successfully`, {
      variant: "success",
    });

    const copyValues = structuredClone(formValues);
    copyValues.parameters.params = params;
    copyValues.parameters.scope.columns = scopeColumns.map((c) => c.columnName);
    handleClose();

    console.log("Saving explorer with params:", copyValues);
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
          setStep={setStep}
        />
      )}

      {step === 1 && (
        <ParameterStepExplorer
          explorer={tool.name}
          initialParams={initialParams}
          handleSaveExplorer={handleSaveExplorer}
          setStep={setStep}
        />
      )}
    </Box>
  );
}
