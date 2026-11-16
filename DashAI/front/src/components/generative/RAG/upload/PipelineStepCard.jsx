import { useCallback, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { Box, IconButton, Tooltip, Typography } from "@mui/material";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import CloseIcon from "@mui/icons-material/Close";
import ComponentDownloadControl, {
  useModelDownloadGate,
} from "../../../models/model/ComponentDownloadControl";
import DescriptionText from "../../../shared/DescriptionText";
import FormSchema from "../../../shared/FormSchema";
import FormSchemaContainer from "../../../shared/FormSchemaContainer";
import { documentConverterTypes } from "./uploadConstants";

/** Height cap for one step's parameter form, so the dialog keeps one scroll. */
const PARAMETERS_MAX_HEIGHT = 240;

/**
 * @param {object} converter - A document converter component.
 * @returns {string} The label to show for it.
 */
function converterLabel(converter) {
  return converter.display_name || converter.name;
}

/**
 * @param {object} converter - A document converter component.
 * @returns {string} Its description, wherever the backend put it.
 */
function converterDescription(converter) {
  return converter?.description ?? converter?.schema?.description ?? "";
}

/**
 * One step of the processing pipeline: header, scope caption and parameters.
 *
 * Living in its own component is what allows `useModelDownloadGate` to run per
 * step: hooks cannot be called in a loop, and every step has its own download
 * state and its own parameter form. The form is keyed by the step key, so
 * reordering the list preserves the values the user already typed.
 *
 * @param {object}   props
 * @param {number}   props.position - 1-based position of the step.
 * @param {string}   props.stepKey - Stable key of the step.
 * @param {object}   props.converter - The converter this step runs.
 * @param {Function} props.registerFormRef - Registers/unregisters the form ref.
 * @param {Function} props.onFormErrorChange - Reports validation errors.
 * @param {Function} props.onDownloadGateChange - Reports a missing download.
 * @param {Function} props.onRemove - Removes the step.
 * @param {Function} props.onMoveUp - Moves the step up.
 * @param {Function} props.onMoveDown - Moves the step down.
 * @param {boolean}  props.canMoveUp - Whether moving up is possible.
 * @param {boolean}  props.canMoveDown - Whether moving down is possible.
 * @param {boolean}  props.disabled - Whether the upload already started.
 * @returns {JSX.Element}
 */
function PipelineStepCard({
  position,
  stepKey,
  converter,
  registerFormRef,
  onFormErrorChange,
  onDownloadGateChange,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  disabled,
}) {
  const { t } = useTranslation("generative");
  const formRef = useRef(null);
  const { modelNotDownloaded } = useModelDownloadGate(
    converter,
    converter.name,
  );
  const description = converterDescription(converter);
  const types = documentConverterTypes(converter);

  useEffect(() => {
    registerFormRef(stepKey, formRef);
    return () => registerFormRef(stepKey, null);
  }, [stepKey, registerFormRef]);

  useEffect(() => {
    onDownloadGateChange(stepKey, modelNotDownloaded);
    return () => onDownloadGateChange(stepKey, false);
  }, [stepKey, modelNotDownloaded, onDownloadGateChange]);

  const setError = useCallback(
    (hasError) => onFormErrorChange(stepKey, hasError),
    [stepKey, onFormErrorChange],
  );

  const runsOn =
    types.length === 0
      ? t("generative:documentUpload.pipelineRunsOnAll")
      : t("generative:documentUpload.pipelineRunsOn", {
          types: types.join(", "),
        });

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1,
        p: 1.5,
        border: 1,
        borderColor: "divider",
        borderRadius: 1,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 0.5 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ display: "block", lineHeight: 1.5 }}
          >
            {t("generative:documentUpload.pipelineStep", { number: position })}
          </Typography>
          <Typography variant="subtitle2" noWrap sx={{ fontWeight: 600 }}>
            {converterLabel(converter)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {runsOn}
          </Typography>
        </Box>
        <Tooltip title={t("generative:documentUpload.pipelineMoveUp")}>
          <span>
            <IconButton
              size="small"
              aria-label={t("generative:documentUpload.pipelineMoveUp")}
              onClick={onMoveUp}
              disabled={disabled || !canMoveUp}
              sx={{ color: "text.secondary" }}
            >
              <ArrowUpwardIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title={t("generative:documentUpload.pipelineMoveDown")}>
          <span>
            <IconButton
              size="small"
              aria-label={t("generative:documentUpload.pipelineMoveDown")}
              onClick={onMoveDown}
              disabled={disabled || !canMoveDown}
              sx={{ color: "text.secondary" }}
            >
              <ArrowDownwardIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title={t("generative:documentUpload.pipelineRemove")}>
          <span>
            <IconButton
              size="small"
              color="error"
              aria-label={t("generative:documentUpload.pipelineRemove")}
              onClick={onRemove}
              disabled={disabled}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </Box>

      {description && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ whiteSpace: "pre-line" }}
        >
          <DescriptionText text={description} />
        </Typography>
      )}

      <ComponentDownloadControl component={converter} />

      <Box
        sx={{
          maxHeight: PARAMETERS_MAX_HEIGHT,
          overflowY: "auto",
          overscrollBehavior: "contain",
        }}
      >
        <FormSchemaContainer>
          <FormSchema
            key={stepKey}
            autoSave
            model={converter.name}
            formSubmitRef={formRef}
            setError={setError}
            initialValues={{}}
            excludeFields={["drop_source_columns"]}
            showBorder={false}
            hideButtons
          />
        </FormSchemaContainer>
      </Box>
    </Box>
  );
}

PipelineStepCard.propTypes = {
  position: PropTypes.number.isRequired,
  stepKey: PropTypes.string.isRequired,
  converter: PropTypes.object.isRequired,
  registerFormRef: PropTypes.func.isRequired,
  onFormErrorChange: PropTypes.func.isRequired,
  onDownloadGateChange: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  onMoveUp: PropTypes.func.isRequired,
  onMoveDown: PropTypes.func.isRequired,
  canMoveUp: PropTypes.bool.isRequired,
  canMoveDown: PropTypes.bool.isRequired,
  disabled: PropTypes.bool,
};

export default PipelineStepCard;
