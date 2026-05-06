import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  Breadcrumbs,
  CircularProgress,
  IconButton,
  Link,
  TextField,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createDataset } from "../../api/datasets";
import {
  getComponentInfo,
  importHubDataset,
  previewHubDataset,
} from "../../api/hub";
import ComponentSelector from "../custom/ComponentSelector";
import PreviewDataset from "../notebooks/datasetCreation/PreviewDataset";

export default function HubImportPanel({
  dataset,
  sourceName,
  compatibleComponents = [],
  step,
  onStepChange,
  selectedLoader,
  onSelectedLoaderChange,
  formValues = {},
  formHasErrors = false,
  onCancel,
  onImported,
}) {
  const { t } = useTranslation(["hub", "common", "datasets"]);
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const [localStep, setLocalStep] = useState(0);
  const [localSelectedLoader, setLocalSelectedLoader] = useState(null);
  const stepValue = step ?? localStep;
  const setStepValue = onStepChange ?? setLocalStep;
  const selectedValue = selectedLoader ?? localSelectedLoader;

  const [dataloaders, setDataloaders] = useState([]);
  const [loadingDataloaders, setLoadingDataloaders] = useState(false);

  const [name, setName] = useState("");
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const [columnTypes, setColumnTypes] = useState({});
  const [columnRenames, setColumnRenames] = useState({});
  const [importing, setImporting] = useState(false);
  const previewDebounceRef = useRef(null);

  useEffect(() => {
    if (!dataset || !sourceName) return;
    setStepValue(0);
    setName(dataset.name || "");
    setLocalSelectedLoader(null);
    onSelectedLoaderChange?.(null);
    setDataloaders([]);
    setPreviewData(null);
    setPreviewError(false);
    setColumnTypes({});
    setColumnRenames({});
  }, [dataset?.id, sourceName, onSelectedLoaderChange, setStepValue]);

  useEffect(() => {
    if (!compatibleComponents.length) {
      setDataloaders([]);
      setLocalSelectedLoader(null);
      onSelectedLoaderChange?.(null);
      return;
    }

    let isMounted = true;
    setLoadingDataloaders(true);
    Promise.all(compatibleComponents.map(getComponentInfo))
      .then((infos) => {
        if (!isMounted) return;
        setDataloaders(infos);
        if (infos.length === 1) {
          setLocalSelectedLoader(infos[0]);
          onSelectedLoaderChange?.(infos[0]);
        }
      })
      .catch(() => {
        if (isMounted) setDataloaders([]);
      })
      .finally(() => {
        if (isMounted) setLoadingDataloaders(false);
      });

    return () => {
      isMounted = false;
    };
  }, [compatibleComponents]);

  useEffect(() => {
    if (stepValue !== 1 || !dataset || !sourceName) return;

    let isMounted = true;
    if (previewDebounceRef.current) {
      clearTimeout(previewDebounceRef.current);
    }

    setPreviewData(null);
    setPreviewLoading(true);
    setPreviewError(false);

    const rows = Number(formValues?.inference_rows);
    const effectiveRows = Number.isFinite(rows)
      ? Math.min(Math.max(2, rows), 500)
      : 100;

    previewDebounceRef.current = setTimeout(() => {
      previewHubDataset(sourceName, dataset.id, effectiveRows)
        .then((data) => {
          if (!isMounted) return;
          setPreviewData(data);
          setColumnTypes(data.inferred_types || {});
        })
        .catch(() => {
          if (isMounted) setPreviewError(true);
        })
        .finally(() => {
          if (isMounted) setPreviewLoading(false);
        });
    }, 350);

    return () => {
      isMounted = false;
      if (previewDebounceRef.current) {
        clearTimeout(previewDebounceRef.current);
      }
    };
  }, [
    stepValue,
    dataset?.id,
    sourceName,
    selectedValue?.name,
    JSON.stringify(formValues || {}),
  ]);

  const handleColumnRename = useCallback((oldName, newName) => {
    setColumnRenames((prev) => ({ ...prev, [oldName]: newName }));
  }, []);

  const handleImport = async () => {
    if (!name.trim() || !dataset || !selectedValue || formHasErrors) return;
    setImporting(true);
    try {
      const created = await createDataset(name.trim());
      await importHubDataset(sourceName, dataset.id, created.id, {
        dataloader: selectedValue.name,
        dataloader_params: formValues,
        inferred_types: columnTypes,
        column_renames: columnRenames,
      });
      enqueueSnackbar(t("hub:importSuccess"), { variant: "success" });
      onImported?.();
    } catch {
      enqueueSnackbar(t("hub:importError"), { variant: "error" });
    } finally {
      setImporting(false);
    }
  };

  const canProceed = !!selectedValue?.name;
  const canImport =
    !!selectedValue?.name &&
    !!name.trim() &&
    !previewLoading &&
    !previewError &&
    !!previewData &&
    !formHasErrors &&
    !importing;

  return (
    <Box
      sx={{ height: "100%", display: "flex", flexDirection: "column", p: 1 }}
    >
      <Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <IconButton
            onClick={() => navigate("/app/data")}
            size="small"
            sx={{
              color: "text.secondary",
              "&:hover": {
                color: "primary.main",
                backgroundColor: "action.hover",
              },
            }}
            aria-label={t("common:back")}
          >
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Breadcrumbs aria-label="breadcrumb">
            <Link
              underline="hover"
              color="inherit"
              href="#"
              onClick={(e) => {
                e.preventDefault();
                navigate("/app/data");
              }}
            >
              {t("common:datasets")}
            </Link>
            <Link
              underline="hover"
              color="inherit"
              href="#"
              onClick={(e) => {
                e.preventDefault();
                navigate("/app/hub");
              }}
            >
              {t("common:hub")}
            </Link>
            <Typography color="text.primary">
              {t("hub:importDataset")}
            </Typography>
          </Breadcrumbs>
        </Box>
      </Box>

      <Box sx={{ p: 2, flex: 1, overflowY: "auto" }}>
        {stepValue === 0 && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 2,
              height: "100%",
              minHeight: 0,
            }}
          >
            <Box>
              <Typography variant="h5" component="h1">
                {t("hub:stepDataloaderTitle")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t("hub:stepDataloaderSubtitle")}
              </Typography>
            </Box>

            {loadingDataloaders ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress />
              </Box>
            ) : compatibleComponents.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                {t("hub:noCompatibleDataloaders")}
              </Typography>
            ) : (
              <Box sx={{ flex: 1, minHeight: 0 }}>
                <ComponentSelector
                  components={dataloaders}
                  selected={selectedValue}
                  onSelect={(item) => {
                    setLocalSelectedLoader(item);
                    onSelectedLoaderChange?.(item);
                  }}
                  searchPlaceholder={t("datasets:searchDataloaders", {
                    defaultValue: "Search data loaders...",
                  })}
                />
              </Box>
            )}
          </Box>
        )}

        {stepValue === 1 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Box>
              <Typography variant="h5" component="h1">
                {t("hub:stepPreviewTitle")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t("hub:stepPreviewSubtitle")}
              </Typography>
            </Box>
            <TextField
              label={t("hub:datasetName")}
              value={name}
              onChange={(e) => setName(e.target.value)}
              fullWidth
            />

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
      </Box>

      <Box
        sx={{
          p: 2,
          borderTop: 1,
          borderColor: "divider",
          display: "flex",
          justifyContent: "space-between",
          gap: 1,
        }}
      >
        {stepValue === 0 ? (
          <Button variant="outlined" onClick={onCancel}>
            {t("common:cancel")}
          </Button>
        ) : (
          <Button variant="outlined" onClick={() => setStepValue(0)}>
            {t("common:back")}
          </Button>
        )}

        {stepValue === 0 ? (
          <Button
            variant="contained"
            onClick={() => setStepValue(1)}
            disabled={!canProceed}
          >
            {t("common:next")}
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleImport}
            disabled={!canImport}
          >
            {importing ? t("hub:importing") : t("hub:importDataset")}
          </Button>
        )}
      </Box>
    </Box>
  );
}
