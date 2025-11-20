import React, { useState } from "react";
import { GridActionsCellItem } from "@mui/x-data-grid";
import { Edit } from "@mui/icons-material";
import { updateRunParameters } from "../../../api/run";
import FormSchemaDialog from "../../shared/FormSchemaDialog";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import { Box } from "@mui/system";

export default function EditRunDialog({ run, onRun }) {
  const isRunning = run.status === "Started" || run.status === "Delivered";
  if (isRunning) {
    return null;
  }
  const [open, setOpen] = useState(false);

  return (
    <>
      <GridActionsCellItem
        icon={<Edit />}
        label="Edit Run"
        onClick={() => setOpen(true)}
      />
      <FormSchemaDialog
        modelToConfigure={run.model_name}
        open={open}
        setOpen={setOpen}
        onFormSubmit={() => {}}
      >
        <FormSchemaWithSelectedModel
          onFormSubmit={async (values) => {
            const newRun = { ...run, parameters: values };
            await updateRunParameters(run.id, values);
            setOpen(false);
            await onRun(newRun);
          }}
          modelToConfigure={run.model_name}
          initialValues={run.parameters}
          onCancel={() => setOpen(false)}
        />
      </FormSchemaDialog>
    </>
  );
}
