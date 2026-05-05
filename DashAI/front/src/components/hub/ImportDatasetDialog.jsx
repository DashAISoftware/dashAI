import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  Radio,
  RadioGroup,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { createDataset } from "../../api/datasets";
import { getComponentInfo, importHubDataset, previewHubDataset } from "../../api/hub";
import ParameterForm from "../configurableObject/ParameterForm";
import PreviewDataset from "../notebooks/datasetCreation/PreviewDataset";

const STEPS = ["hub:stepFormat", "hub:stepParameters", "hub:stepPreview"];

/**
 * Dialog that walks the user through format selection, dataloader parameter
 * configuration, dataset preview, and final import into DashAI.
 *
 * @param {boolean} open - Whether the dialog is open.
 * @param {function} onClose - Called when the dialog is dismissed.
 * @param {string} sourceName - DatasetSource class name.
 * @param {object|null} dataset - DatasetEntry to import.
 * @param {string[]} compatibleComponents - DataLoader class names compatible with this source.
 * @param {function} onImported - Called after successful import.
 */
export default function ImportDatasetDialog({
  open,
  onClose,
  sourceName,
  dataset,
  compatibleComponents = [],
  onImported,
}) {
  const { t } = useTranslation(["hub", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const paramsFormRef = useRef(null);

  const [step, setStep] = useState(0);
  const [selectedLoader, setSelectedLoader] = useState(null);
  const [loaderInfos, setLoaderInfos] = useState({});
  const [loadingInfos, setLoadingInfos] = useState(false);
  const [loaderParams, setLoaderParams] = useState({});

  const [name, setName] = useState("");
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const [columnTypes, setColumnTypes] = useState({});
  const [columnRenames, setColumnRenames] = useState({});
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    if (!open || !dataset || !sourceName) return;
    setName(dataset.name || "");
    setStep(0);
    setSelectedLoader(compatibleComponents.length === 1 ? compatibleComponents[0] : null);
    setLoaderParams({});
    setPreviewData(null);
    setPreviewError(false);
    setColumnTypes({});
    setColumnRenames({});

    if (!compatibleComponents.length) return;
    setLoadingInfos(true);
    Promise.all(compatibleComponents.map(getComponentInfo))
      .then((infos) => {
        const map = {};
        infos.forEach((info) => {
          map[info.name] = info;
        });
        setLoaderInfos(map);
      })
      .catch(() => {})
      .finally(() => setLoadingInfos(false));
  }, [open, dataset, sourceName, compatibleComponents]);

  const fetchPreview = useCallback(() => {
    setPreviewData(null);
    setPreviewLoading(true);
    setPreviewError(false);
    previewHubDataset(sourceName, dataset.id, 100)
      .then((data) => {
        setPreviewData(data);
        setColumnTypes(data.inferred_types || {});
      })
      .catch(() => setPreviewError(true))
      .finally(() => setPreviewLoading(false));
  }, [sourceName, dataset]);

  const handleColumnRename = useCallback((oldName, newName) => {
    setColumnRenames((prev) => ({ ...prev, [oldName]: newName }));
  }, []);

  const handleParamsSubmit = useCallback(
    (values) => {
      setLoaderParams(values);
      fetchPreview();
      setStep(2);
    },
    [fetchPreview],
  );

  const handleNext = () => {
    if (step === 0) {
      setStep(1);
    } else if (step === 1) {
      if (paramsFormRef.current) {
        paramsFormRef.current.handleSubmit();
      } else {
        fetchPreview();
        setStep(2);
      }
    }
  };

  const handleBack = () => setStep((s) => Math.max(0, s - 1));

  const handleImport = async () => {
    if (!name.trim() || !dataset) return;
    setImporting(true);
    try {
      const created = await createDataset(name.trim());
      await importHubDataset(sourceName, dataset.id, created.id, {
        dataloader: selectedLoader,
        dataloader_params: loaderParams,
        inferred_types: columnTypes,
        column_renames: columnRenames,
      });
      enqueueSnackbar(t("hub:importSuccess"), { variant: "success" });
      onImported?.();
      onClose();
    } catch {
      enqueueSnackbar(t("hub:importError"), { variant: "error" });
    } finally {
      setImporting(false);
    }
  };

  const selectedLoaderInfo = selectedLoader ? loaderInfos[selectedLoader] : null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>{t("hub:importDataset")}</DialogTitle>
      <DialogContent dividers>
        <Stepper activeStep={step} sx={{ mb: 3 }}>
          {STEPS.map((key) => (
            <Step key={key}>
              <StepLabel>{t(key)}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {/* Step 0: Format selection */}
        {step === 0 && (
          <Box>
            {loadingInfos ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress />
              </Box>
            ) : (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {t("hub:selectFormatDescription")}
                </Typography>
                <FormControl>
                  <RadioGroup
                    value={selectedLoader ?? ""}
                    onChange={(e) => setSelectedLoader(e.target.value)}
                  >
                    {compatibleComponents.map((loaderName) => {
                      const info = loaderInfos[loaderName];
                      return (
                        <FormControlLabel
                          key={loaderName}
                          value={loaderName}
                          control={<Radio />}
                          label={
                            <Box>
                              <Typography variant="body2">
                                {info?.display_name || loaderName}
                              </Typography>
                              {info?.description && (
                                <Typography variant="caption" color="text.secondary">
                                  {info.description}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                      );
                    })}
                  </RadioGroup>
                </FormControl>
              </>
            )}
          </Box>
        )}

        {/* Step 1: Dataloader parameters */}
        {step === 1 && (
          <Box>
            {!selectedLoaderInfo ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress />
              </Box>
            ) : selectedLoaderInfo.schema ? (
              <ParameterForm
                parameterSchema={selectedLoaderInfo.schema}
                onFormSubmit={handleParamsSubmit}
                submitButton={false}
                formSubmitRef={paramsFormRef}
              />
            ) : (
              <Typography variant="body2" color="text.secondary">
                {t("hub:noParameters")}
              </Typography>
            )}
          </Box>
        )}

        {/* Step 2: Preview and confirm */}
        {step === 2 && (
          <Box>
            <Box sx={{ mb: 2 }}>
              <TextField
                label={t("hub:datasetName")}
                value={name}
                onChange={(e) => setName(e.target.value)}
                fullWidth
              />
            </Box>

            {previewLoading && (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress />
              </Box>
            )}

            {previewError && !previewLoading && (
              <Typography color="error">{t("hub:previewError")}</Typography>
            )}

            {!previewLoading && !previewError && previewData && (
              <PreviewDataset
                initialData={previewData}
                onTypesChanged={setColumnTypes}
                onColumnRename={handleColumnRename}
              />
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={importing}>
          {t("common:cancel")}
        </Button>
        {step > 0 && (
          <Button onClick={handleBack} disabled={importing}>
            {t("common:back")}
          </Button>
        )}
        {step < 2 ? (
          <Button
            variant="contained"
            onClick={handleNext}
            disabled={loadingInfos || (step === 0 && !selectedLoader)}
          >
            {t("common:next")}
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleImport}
            disabled={importing || !name.trim() || previewError || previewLoading}
          >
            {importing ? t("hub:importing") : t("common:confirm")}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
