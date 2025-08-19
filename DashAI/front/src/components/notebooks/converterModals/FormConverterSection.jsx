import React, { useEffect, useState } from "react";
import { Box, Typography, Button, IconButton, Tooltip } from "@mui/material";

import { saveConverterList } from "../../../api/converter";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import { useSnackbar } from "notistack";
import { ViewColumn } from "@mui/icons-material";
import HelpIcon from "@mui/icons-material/Help";
import ConverterClassColumnModal from "./ConverterClassColumnModal";
import ParameterStepConverter from "./ParameterStepConverter";
import ScopeStepConverter from "./ScopeStepConverter";

export default function FormConverterSection({
  step,
  setStep,
  handleClose,
  tool,
  notebook,
}) {
  const [targetColumn, setTargetColumn] = useState(null);
  const [rows, setRows] = useState([]);
  const [columns, setColumns] = useState([]);
  const [parameters, setParameters] = useState({});

  const [formValues, setFormValues] = useState({
    notebook_id: notebook.id,
    converter: tool.name,
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

  const handleSaveConverter = async (params) => {
    enqueueSnackbar(`Converter ${tool.name} created successfully `, {
      variant: "success",
    });

    const data = {
      notebook_id: notebook.id,
      converter: tool.name,
      parameters: {
        params: parameters,
        scope: {
          columns: columns,
          rows: rows,
        },
        order: 1,
        target_index: targetColumn,
      },
    };
    handleClose();

    console.log("Saving converter with params:", data);
  };

  useEffect(() => {
    const copyValues = structuredClone(formValues);
    copyValues.parameters.target_index = targetColumn;
    setFormValues(copyValues);
  }, [targetColumn]);

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
        <ScopeStepConverter
          targetColumn={targetColumn}
          setTargetColumn={setTargetColumn}
          rows={rows}
          setRows={setRows}
          columns={columns}
          setColumns={setColumns}
          notebook={notebook}
          setStep={setStep}
        />
      )}

      {step === 1 && (
        <ParameterStepConverter
          converter={tool.name}
          initialParams={{}}
          handleSaveConverter={handleSaveConverter}
          setStep={setStep}
        />
      )}
    </Box>
  );
}
