import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
} from "@mui/material";
import { Save, Cancel, Close as CloseIcon } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import RetrainConfirmDialog from "./RetrainConfirmDialog";
import RunEditForm from "./RunEditForm";
import useRunEditForm from "../../hooks/useRunEditForm";

/**
 * Editable-parameters dialog for a run — the same form used to configure it
 * before training, pre-filled with its current values. Shared by RunCard's
 * "Editar" button and the compact model card's quick-edit action so both
 * entry points open the exact same modal.
 */
export default function RunEditDialog({
  run,
  session,
  existingRuns = [],
  onRefresh,
  open,
  onClose,
}) {
  const { t } = useTranslation(["models", "common"]);

  const formProps = useRunEditForm({
    run,
    session,
    existingRuns,
    onRefresh,
    onSaved: onClose,
    enabled: open,
  });

  const {
    canSave,
    operationsCount,
    isSaving,
    saveConfirmOpen,
    setSaveConfirmOpen,
    doSave,
    handleSaveEdit,
    taskName,
  } = formProps;

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { minHeight: "500px" } }}
      >
        <DialogTitle sx={{ bgcolor: "background.paper" }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Typography variant="h6" component="span">
              {t("models:label.editRun")}
            </Typography>
            <IconButton
              size="small"
              onClick={onClose}
              sx={{ color: "text.secondary" }}
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
          <RunEditForm run={run} {...formProps} />
        </DialogContent>

        <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
          <Button
            variant="outlined"
            startIcon={<Cancel />}
            onClick={onClose}
            disabled={isSaving}
          >
            {t("common:cancel")}
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSaveEdit}
            disabled={isSaving || !canSave}
          >
            {isSaving ? t("common:saving") : t("common:save")}
          </Button>
        </DialogActions>
      </Dialog>

      <RetrainConfirmDialog
        mode="save"
        open={saveConfirmOpen}
        onClose={() => setSaveConfirmOpen(false)}
        onConfirm={doSave}
        run={run}
        operationsCount={operationsCount}
      />
    </>
  );
}

RunEditDialog.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    model_name: PropTypes.string,
    parameters: PropTypes.object,
    optimizer_name: PropTypes.string,
    optimizer_parameters: PropTypes.object,
    goal_metric: PropTypes.string,
  }).isRequired,
  session: PropTypes.shape({
    task_name: PropTypes.string,
  }),
  existingRuns: PropTypes.array,
  onRefresh: PropTypes.func,
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};
