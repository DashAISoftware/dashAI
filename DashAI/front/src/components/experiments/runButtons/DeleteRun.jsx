import React, { useState } from "react";
import { GridActionsCellItem } from "@mui/x-data-grid";
import DeleteIcon from "@mui/icons-material/Delete";
import { deleteRun } from "../../../api/run";
import { useSnackbar } from "notistack";
import DeleteConfirmationModal from "../../threeSectionLayout/DeleteConfirmationModal";

export default function DeleteRun({ run, onRunDelete }) {
  const isRunning = run.status === "Started" || run.status === "Delivered";
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  if (isRunning) {
    return null;
  }

  return (
    <>
      <GridActionsCellItem
        icon={<DeleteIcon />}
        label="Delete Run"
        onClick={() => {
          setOpen(true);
        }}
      />
      {open && (
        <DeleteConfirmationModal
          open={open}
          onClose={() => setOpen(false)}
          onConfirm={async () => {
            try {
              await deleteRun(run.id);
              onRunDelete(run.id);
              enqueueSnackbar("Run deleted successfully", {
                variant: "success",
              });
            } catch (error) {
              console.error("Error deleting run:", error);
              enqueueSnackbar("Error deleting run", { variant: "error" });
            } finally {
              setOpen(false);
            }
          }}
          content="Are you sure you want to delete this run? This action cannot be undone."
        />
      )}
    </>
  );
}
