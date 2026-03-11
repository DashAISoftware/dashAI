import React, { useState } from "react";
import { GridActionsCellItem } from "@mui/x-data-grid";
import DeleteIcon from "@mui/icons-material/Delete";
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
      <GridActionsCellItem
        icon={<DeleteIcon />}
        label={t("button.deleteRun")}
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
              enqueueSnackbar(t("message.runDeletedSuccessfully"), {
                variant: "success",
              });
            } catch (error) {
              console.error("Error deleting run:", error);
              const detail =
                error?.response?.data?.detail || error?.message || "";
              enqueueSnackbar(
                detail
                  ? `${t("message.errorDeletingRun")}: ${detail}`
                  : t("message.errorDeletingRun"),
                {
                  variant: "error",
                },
              );
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
