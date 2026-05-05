import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { createDataset } from "../../api/datasets";
import { importHubDataset, previewHubDataset } from "../../api/hub";
import PreviewDataset from "../notebooks/datasetCreation/PreviewDataset";

/**
 * Dialog that previews a Hub dataset and imports it into DashAI on confirm.
 *
 * @param {boolean} open - Whether the dialog is open.
 * @param {function} onClose - Called when the dialog is dismissed.
 * @param {string} sourceName - DatasetSource class name.
 * @param {object|null} dataset - DatasetEntry to import.
 * @param {function} onImported - Called with job_id after successful enqueue.
 */
export default function ImportDatasetDialog({
  open,
  onClose,
  sourceName,
  dataset,
  onImported,
}) {
  const { t } = useTranslation(["hub", "common"]);
  const { enqueueSnackbar } = useSnackbar();

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
    setPreviewData(null);
    setPreviewLoading(true);
    setPreviewError(false);
    setColumnTypes({});
    setColumnRenames({});

    previewHubDataset(sourceName, dataset.id, 100)
      .then((data) => {
        setPreviewData(data);
        setColumnTypes(data.inferred_types || {});
      })
      .catch(() => setPreviewError(true))
      .finally(() => setPreviewLoading(false));
  }, [open, dataset, sourceName]);

  const handleColumnRename = useCallback((oldName, newName) => {
    setColumnRenames((prev) => ({ ...prev, [oldName]: newName }));
  }, []);

  const handleImport = async () => {
    if (!name.trim() || !dataset) return;
    setImporting(true);
    try {
      const created = await createDataset(name.trim());
      await importHubDataset(sourceName, dataset.id, created.id, {
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

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>{t("hub:importDataset")}</DialogTitle>
      <DialogContent dividers>
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
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={importing}>
          {t("common:cancel")}
        </Button>
        <Button
          variant="contained"
          onClick={handleImport}
          disabled={importing || !name.trim() || previewError || previewLoading}
        >
          {importing ? t("hub:importing") : t("common:confirm")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
