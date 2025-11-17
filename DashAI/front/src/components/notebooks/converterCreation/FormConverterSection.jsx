import React, { useState } from "react";
import { Box } from "@mui/material";
import { saveConverterList } from "../../../api/converter";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useSnackbar } from "notistack";
import ParameterStepConverter from "./ParameterStepConverter";
import ScopeStepConverter from "./ScopeStepConverter";
import { startJobPolling } from "../../../utils/jobPoller";
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
        target: targetColumn,
      },
    };

    saveConverterList(data)
      .then((response) => {
        const data = { ...response, type: "converter" };
        setExplorersAndConverters((prev) => [...prev, data]);
        enqueueSnackbar(`Converter ${tool.name} created successfully`, {
          variant: "success",
        });

        enqueueConverterJob(data.id)
          .then((jobResponse) => {
            if (jobResponse && jobResponse.id) {
              startJobPolling(
                jobResponse.id,

                (result) => {
                  enqueueSnackbar(
                    `Converter ${tool.name} processed successfully`,
                    {
                      variant: "success",
                    },
                  );

                  setExplorersAndConverters((prev) =>
                    prev.map((item) =>
                      item.id === data.id && item.type === "converter"
                        ? { ...item, status: 3 }
                        : item,
                    ),
                  );
                },

                (result) => {
                  console.error("Converter job failed:", result);
                  enqueueSnackbar(
                    `Error processing converter: ${
                      result.error || "Unknown error"
                    }`,
                    { variant: "error" },
                  );

                  setExplorersAndConverters((prev) =>
                    prev.map((item) =>
                      item.id === data.id && item.type === "converter"
                        ? { ...item, status: 4 }
                        : item,
                    ),
                  );
                },
              );
            }
          })
          .catch((error) => {
            console.error("Error enqueuing converter job:", error);
            enqueueSnackbar("Failed to process converter", {
              variant: "error",
            });
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
        overflow: "visible",
        display: "flex",
        flexDirection: "column",
        flexGrow: 1,
        maxHeight: "100%",
      }}
    >
      {step === 0 && (
        <ScopeStepConverter
          supervised={tool.metadata.supervised}
          targetColumn={targetColumn}
          setTargetColumn={setTargetColumn}
          tool={tool}
          rows={rows}
          setRows={setRows}
          columns={columns}
          setColumns={setColumns}
          notebook={notebook}
          nextStep={
            Object.values(tool.schema.properties).length > 0
              ? () => setStep((s) => s + 1)
              : () => handleSaveConverter({})
          }
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
