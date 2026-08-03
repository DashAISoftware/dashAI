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

import { createReport as createReportRequest } from "../../api/report";
import { enqueueReportJob as enqueueReportJobRequest } from "../../api/job";
import { startJobPolling } from "../../utils/jobPoller";
import useSchema from "../../hooks/useSchema";
import SelectSplitStep from "./SelectSplitStep";
import ConfigureReportStep from "./ConfigureReportStep";

const SNACKBAR_AUTO_HIDE_MS = 5000;

/**
 * Creation stepper for one evaluation report, mirroring the explainer
 * creator: pick the split and name it, then configure its parameters, then
 * save. Saving both creates the row and enqueues its job, so the card appears
 * in the central view already computing.
 */
export default function InlineReportCreator({
  open,
  runId,
  reportName,
  displayName,
  onCreated,
  onCancel,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["reports", "common"]);
  const formSubmitRef = useRef(null);

  const defaultNewReport = useMemo(
    () => ({
      run_id: runId,
      report_name: reportName,
      split: "test",
      parameters: null,
    }),
    [runId, reportName],
  );

  // Most reports take no parameters at all, so the configuration step is
  // dropped entirely rather than shown empty: a one step wizard is just a
  // dialog with a Save button, which is what those deserve.
  const { defaultValues, loading: schemaLoading } = useSchema({
    modelName: reportName,
  });
  const hasParameters =
    Boolean(defaultValues) && Object.keys(defaultValues).length > 0;

  const steps = useMemo(() => {
    const labels = [t("reports:label.selectSplit")];
    if (hasParameters) {
      labels.push(t("reports:label.configureParameters"));
    }
    return labels;
  }, [hasParameters, t]);

  const [activeStep, setActiveStep] = useState(0);
  const [nextEnabled, setNextEnabled] = useState(false);
  const [newReport, setNewReport] = useState(defaultNewReport);
  const [isLoading, setIsLoading] = useState(false);

  const resetState = () => {
    setActiveStep(0);
    setNewReport(defaultNewReport);
    setNextEnabled(false);
  };

  useEffect(() => {
    if (!open) resetState();
  }, [open]);

  const enqueueJob = async (reportId) => {
    const response = await enqueueReportJobRequest(reportId);
    enqueueSnackbar(t("reports:message.created"), {
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
          console.error("Report job failed:", result);
          enqueueSnackbar(t("reports:message.failed"), {
            variant: "error",
            autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
          });
          if (onCreated) onCreated();
        },
      );
    }
    return response;
  };

  const uploadNewReport = async () => {
    try {
      setIsLoading(true);
      const response = await createReportRequest(
        newReport.run_id,
        newReport.report_name,
        newReport.split,
        newReport.parameters ?? {},
      );
      await enqueueJob(response.id);
      if (onCreated) onCreated();
      return true;
    } catch (error) {
      enqueueSnackbar(t("reports:error.create"), {
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

    const isSuccess = await uploadNewReport();
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
            {t("reports:label.newReport")}
            {`: ${displayName || reportName}`}
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
            newReport={newReport}
            setNewReport={setNewReport}
            setNextEnabled={setNextEnabled}
          />
        )}
        {hasParameters && activeStep === 1 && (
          <ConfigureReportStep
            newReport={newReport}
            setNewReport={setNewReport}
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
          // report that turns out to have a parameter step.
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

InlineReportCreator.propTypes = {
  open: PropTypes.bool.isRequired,
  runId: PropTypes.number.isRequired,
  reportName: PropTypes.string.isRequired,
  displayName: PropTypes.string,
  onCreated: PropTypes.func,
  onCancel: PropTypes.func.isRequired,
};
