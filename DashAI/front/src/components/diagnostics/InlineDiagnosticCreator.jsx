import React, { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Step,
  StepLabel,
  Stepper,
  Typography,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import { LoadingButton } from "@mui/lab";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

import { createDiagnostic as createDiagnosticRequest } from "../../api/diagnostic";
import { enqueueDiagnosticJob as enqueueDiagnosticJobRequest } from "../../api/job";
import { startJobPolling } from "../../utils/jobPoller";
import useSchema from "../../hooks/useSchema";
import SelectSplitStep from "./SelectSplitStep";
import ConfigureDiagnosticStep from "./ConfigureDiagnosticStep";

const SNACKBAR_AUTO_HIDE_MS = 5000;

/**
 * Creation stepper for one evaluation diagnostic, mirroring the explainer
 * creator: pick the split and name it, then configure its parameters, then
 * save. Saving both creates the row and enqueues its job, so the card appears
 * in the central view already computing.
 */
export default function InlineDiagnosticCreator({
  open,
  runId,
  diagnosticName,
  displayName,
  onCreated,
  onCancel,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["diagnostics", "common"]);
  const formSubmitRef = useRef(null);

  const defaultNewDiagnostic = useMemo(
    () => ({
      run_id: runId,
      diagnostic_name: diagnosticName,
      split: "test",
      parameters: null,
    }),
    [runId, diagnosticName],
  );

  // Most diagnostics take no parameters at all, so the configuration step is
  // dropped entirely rather than shown empty: a one step wizard is just a
  // dialog with a Save button, which is what those deserve.
  const { defaultValues, loading: schemaLoading } = useSchema({
    modelName: diagnosticName,
  });
  const hasParameters =
    Boolean(defaultValues) && Object.keys(defaultValues).length > 0;

  const steps = useMemo(() => {
    const labels = [t("diagnostics:label.selectSplit")];
    if (hasParameters) {
      labels.push(t("diagnostics:label.configureParameters"));
    }
    return labels;
  }, [hasParameters, t]);

  const [activeStep, setActiveStep] = useState(0);
  const [nextEnabled, setNextEnabled] = useState(false);
  const [newDiagnostic, setNewDiagnostic] = useState(defaultNewDiagnostic);
  const [isLoading, setIsLoading] = useState(false);

  const resetState = () => {
    setActiveStep(0);
    setNewDiagnostic(defaultNewDiagnostic);
    setNextEnabled(false);
  };

  useEffect(() => {
    if (!open) resetState();
  }, [open]);

  const enqueueJob = async (diagnosticId) => {
    const response = await enqueueDiagnosticJobRequest(diagnosticId);
    enqueueSnackbar(t("diagnostics:message.created"), {
      variant: "success",
      autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
    });

    if (response && response.id) {
      startJobPolling(
        response.id,
        () => {
          if (onCreated) onCreated();
        },
        (result) => {
          console.error("Diagnostic job failed:", result);
          enqueueSnackbar(t("diagnostics:message.failed"), {
            variant: "error",
            autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
          });
          if (onCreated) onCreated();
        },
      );
    }
    return response;
  };

  const uploadNewDiagnostic = async () => {
    try {
      setIsLoading(true);
      const response = await createDiagnosticRequest(
        newDiagnostic.run_id,
        newDiagnostic.diagnostic_name,
        newDiagnostic.split,
        newDiagnostic.parameters ?? {},
      );
      await enqueueJob(response.id);
      if (onCreated) onCreated();
      return true;
    } catch (error) {
      enqueueSnackbar(t("diagnostics:error.create"), {
        variant: "error",
        autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
      });
      console.error("Error details:", error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
    setNextEnabled(true);
  };

  const handleNext = async () => {
    if (activeStep < steps.length - 1) {
      setActiveStep((prev) => prev + 1);
      setNextEnabled(false);
      return;
    }

    const isSuccess = await uploadNewDiagnostic();
    if (isSuccess) {
      resetState();
      onCancel();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onCancel}
      maxWidth="lg"
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
            {t("diagnostics:label.newDiagnostic")}
            {`: ${displayName || diagnosticName}`}
          </Typography>
          <IconButton
            onClick={onCancel}
            size="small"
            sx={{ color: "text.secondary" }}
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
        {/* A single step is not a wizard, so the stepper is hidden then. */}
        {steps.length > 1 && (
          <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
            {steps.map((label) => (
              <Step key={label} completed={false}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        )}

        {activeStep === 0 && (
          <SelectSplitStep
            newDiagnostic={newDiagnostic}
            setNewDiagnostic={setNewDiagnostic}
            setNextEnabled={setNextEnabled}
          />
        )}
        {hasParameters && activeStep === 1 && (
          <ConfigureDiagnosticStep
            newDiagnostic={newDiagnostic}
            setNewDiagnostic={setNewDiagnostic}
            setNextEnabled={setNextEnabled}
            formSubmitRef={formSubmitRef}
            defaultValues={defaultValues}
          />
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
        {activeStep > 0 && (
          <Button variant="outlined" onClick={handleBack} disabled={isLoading}>
            {t("common:back")}
          </Button>
        )}
        <LoadingButton
          onClick={handleNext}
          variant="contained"
          color="primary"
          // Held until the schema resolves, so the label cannot say Save on a
          // diagnostic that turns out to have a parameter step.
          disabled={!nextEnabled || isLoading || schemaLoading}
          loading={isLoading}
        >
          {activeStep === steps.length - 1
            ? t("common:save")
            : t("common:next")}
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
}

InlineDiagnosticCreator.propTypes = {
  open: PropTypes.bool.isRequired,
  runId: PropTypes.number.isRequired,
  diagnosticName: PropTypes.string.isRequired,
  displayName: PropTypes.string,
  onCreated: PropTypes.func,
  onCancel: PropTypes.func.isRequired,
};
