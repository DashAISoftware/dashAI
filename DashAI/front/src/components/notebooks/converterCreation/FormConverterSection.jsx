import React, { useState } from "react";
import { Box } from "@mui/material";

import { saveConverterList } from "../../../api/converter";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useSnackbar } from "notistack";
import ParameterStepConverter from "./ParameterStepConverter";
import ScopeStepConverter from "./ScopeStepConverter";
import { enqueueConverterJob, startJobQueue } from "../../../api/job";

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
        target_index: tool.metadata.supervised ? targetColumn : 1,
      },
    };

    saveConverterList(data)
      .then((response) => {
        const data = { ...response, type: "converter" };
        setExplorersAndConverters((prev) => [...prev, data]);
        enqueueSnackbar(`Converter ${tool.name} created successfully `, {
          variant: "success",
        });
        enqueueConverterJob(data.id)
          .then(() => {
            startJobQueue();
          })
          .catch((error) => {
            console.error("Error enqueuing converter job:", error);
          });
      })
      .catch((error) => {
        console.error("Error creating converter:", error);
        enqueueSnackbar("Failed to create converter", { variant: "error" });
      })
      .finally(() => {
        handleClose();
      });
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
          supervised={tool.metadata.supervised}
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
