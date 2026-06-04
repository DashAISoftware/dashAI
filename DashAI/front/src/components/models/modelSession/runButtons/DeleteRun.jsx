import React, { useState } from "react";
import DeleteIcon from "@mui/icons-material/Delete";
import { IconButton, Tooltip } from "@mui/material";
import { deleteRun } from "../../../api/run";
import { useSnackbar } from "notistack";
import DeleteConfirmationModal from "../../threeSectionLayout/DeleteConfirmationModal";
import { useTranslation } from "react-i18next";

export default function DeleteRun({ run, onRunDelete }) {
  const isRunning = run.status === 1 || run.status === 2; // Delivered or Started
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation("experiments");
  const [open, setOpen] = useState(false);
  if (isRunning) {
    return null;
  }

  return (
    <>
      <Tooltip title={t("button.deleteRun")}>
        <span>
          <IconButton
            size="small"
            aria-label={t("button.deleteRun")}
            onClick={() => {
              setOpen(true);
            }}
          >
            <DeleteIcon />
          </IconButton>
        </span>
      </Tooltip>
      {open && (
        <DeleteConfirmationModal
          open={open}
          onClose={() => setOpen(false)}
          onConfirm={async () => {
            try {
              await deleteRun(run.id);
              localStorage.removeItem(`run-${run.id}-active-tab`);
              localStorage.removeItem(`run-${run.id}-results-visible`);
              onRunDelete(run.id);
              enqueueSnackbar(t("message.runDeletedSuccessfully"), {
                variant: "success",
              });
            } catch (error) {
              console.error("Error deleting run:", error);
              enqueueSnackbar(t("message.errorDeletingRun"), {
                variant: "error",
              });
            } finally {
              setOpen(false);
            }
          }}
          content={t("message.confirmDeleteRun")}
        />
      )}
    </>
  );
}
