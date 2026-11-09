import { useCallback, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  MenuItem,
  TextField,
  Typography,
} from "@mui/material";
import PipelineStepCard from "./PipelineStepCard";
import { CONVERTERS_STATUS } from "./uploadConstants";

/**
 * Optional batch-wide converter pipeline of the upload dialog.
 *
 * The converters run on every uploaded file, in order, but each one only sees
 * the content types it declares; a document without matching items skips that
 * step. The list stays visible before any file is selected so a folder of
 * scanned documents can be configured for OCR first.
 *
 * @param {object}   props
 * @param {Array}    props.converters - Document converters available.
 * @param {string}   props.status - Whether the converters were fetched.
 * @param {Array}    props.steps - Ordered `{key, name}` steps.
 * @param {Function} props.onAdd - Adds a converter as a new step.
 * @param {Function} props.onRemove - Removes a step.
 * @param {Function} props.onMoveUp - Moves a step up.
 * @param {Function} props.onMoveDown - Moves a step down.
 * @param {Function} props.registerFormRef - Registers a step's form ref.
 * @param {Function} props.onFormErrorChange - Reports a step's error state.
 * @param {Function} props.onDownloadGateChange - Reports a missing download.
 * @param {Function} props.onRetry - Retries fetching the converters.
 * @param {boolean}  props.disabled - Whether the upload already started.
 * @returns {JSX.Element}
 */
export default function DocumentPipelineEditor({
  converters,
  status,
  steps,
  onAdd,
  onRemove,
  onMoveUp,
  onMoveDown,
  registerFormRef,
  onFormErrorChange,
  onDownloadGateChange,
  onRetry,
  disabled,
}) {
  const { t } = useTranslation(["generative"]);
  const [selectedName, setSelectedName] = useState("");

  const convertersByName = useMemo(() => {
    const byName = new Map();
    for (const converter of converters) {
      byName.set(converter.name, converter);
    }
    return byName;
  }, [converters]);

  const loading = status === CONVERTERS_STATUS.LOADING;
  const failed = status === CONVERTERS_STATUS.ERROR;
  const ready = status === CONVERTERS_STATUS.READY;
  const needsDownload = useMemo(
    () =>
      steps.some((step) =>
        Boolean(convertersByName.get(step.name)?.metadata?.requires_download),
      ),
    [steps, convertersByName],
  );

  const handleSelect = useCallback(
    (event) => {
      const name = event.target.value;
      if (!name) return;
      onAdd(name);
      setSelectedName("");
    },
    [onAdd],
  );

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        minWidth: 0,
        borderTop: 1,
        borderColor: "divider",
        pt: 2,
      }}
    >
      <Typography
        variant="overline"
        color="text.secondary"
        sx={{ display: "block", lineHeight: 2 }}
      >
        {t("generative:documentUpload.pipelineTitle")}
      </Typography>

      <Typography variant="body2" color="text.secondary">
        {t("generative:documentUpload.pipelineHint")}
      </Typography>

      {failed && (
        <Alert
          severity="warning"
          action={
            <Button color="inherit" size="small" onClick={onRetry}>
              {t("generative:documentUpload.pipelineRetry")}
            </Button>
          }
        >
          {t("generative:documentUpload.pipelineLoadersFailed")}
        </Alert>
      )}

      {ready && converters.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          {t("generative:documentUpload.pipelineNoConverters")}
        </Typography>
      )}

      <TextField
        select
        size="small"
        label={t("generative:documentUpload.pipelineAdd")}
        value={selectedName}
        onChange={handleSelect}
        disabled={disabled || !ready || converters.length === 0}
        slotProps={{
          inputLabel: { shrink: true },
          select: { displayEmpty: true },
        }}
        sx={{ alignSelf: "flex-start", minWidth: 260, maxWidth: "100%" }}
      >
        <MenuItem value="" disabled>
          {loading
            ? t("generative:rag.common.loading")
            : t("generative:documentUpload.pipelineAdd")}
        </MenuItem>
        {converters.map((converter) => (
          <MenuItem key={converter.name} value={converter.name}>
            {converter.display_name || converter.name}
          </MenuItem>
        ))}
      </TextField>

      {steps.length === 0 && ready && converters.length > 0 && (
        <Typography variant="body2" color="text.secondary">
          {t("generative:documentUpload.pipelineEmpty")}
        </Typography>
      )}

      {steps.map((step, index) => {
        const converter = convertersByName.get(step.name);
        if (!converter) return null;
        return (
          <PipelineStepCard
            key={step.key}
            position={index + 1}
            stepKey={step.key}
            converter={converter}
            registerFormRef={registerFormRef}
            onFormErrorChange={onFormErrorChange}
            onDownloadGateChange={onDownloadGateChange}
            onRemove={() => onRemove(step.key)}
            onMoveUp={() => onMoveUp(step.key)}
            onMoveDown={() => onMoveDown(step.key)}
            canMoveUp={index > 0}
            canMoveDown={index < steps.length - 1}
            disabled={disabled}
          />
        );
      })}

      <Typography variant="caption" color="text.secondary">
        {t("generative:documentUpload.pipelineSkipHint")}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {t("generative:documentUpload.pipelineImageHint")}
      </Typography>
      {needsDownload && (
        <Typography variant="caption" color="text.secondary">
          {t("generative:documentUpload.pipelineDownloadHint")}
        </Typography>
      )}
    </Box>
  );
}

DocumentPipelineEditor.propTypes = {
  converters: PropTypes.arrayOf(PropTypes.object).isRequired,
  status: PropTypes.string.isRequired,
  steps: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
    }),
  ).isRequired,
  onAdd: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  onMoveUp: PropTypes.func.isRequired,
  onMoveDown: PropTypes.func.isRequired,
  registerFormRef: PropTypes.func.isRequired,
  onFormErrorChange: PropTypes.func.isRequired,
  onDownloadGateChange: PropTypes.func.isRequired,
  onRetry: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};
