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
import { enqueueConverterJob } from "../../../api/job";

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
  const { explorersAndConverters, setExplorersAndConverters } =
    useExplorersAndConverters();
  const { enqueueSnackbar } = useSnackbar();

  const handleSaveConverter = async (params) => {
    const data = {
      notebook_id: notebook.id,
      converter: tool.name,
      parameters: {
        params: params,
        scope: {
          columns: columns,
          rows: rows,
        },
        order: 1,
        target_index: targetColumn,
      },
    };

    saveConverterList(data).then(
      (response) => {
        const data = { ...response, type: "converter" };
        setExplorersAndConverters((prev) => [...prev, data]);
        enqueueSnackbar(`Converter ${tool.name} created successfully `, {
          variant: "success",
        });
        enqueueConverterJob(data.id)
          .then((jobResponse) => {
            console.log("Converter job enqueued successfully:", jobResponse);
          })
          .catch((error) => {
            console.error("Error enqueuing converter job:", error);
          });
      },
      (error) => {
        console.error("Error saving converter:", error);
      },
    );
    console.log("Saving converter with params:", data);
    handleClose();
  };

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
