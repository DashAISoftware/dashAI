import React from "react";
import PropTypes from "prop-types";
import {
  FormControlLabel,
  Checkbox,
  Alert,
  Box,
  Link,
  Collapse,
  Fade,
  Typography,
  MenuItem,
  TextField,
  Divider,
} from "@mui/material";
import { useTranslation } from "react-i18next";

/**
 * Compatible inner splitters per outer splitter type.
 * Group-based outer splitters require group-based inner splitters.
 * TimeSeries outer splitter requires TimeSeries inner splitter.
 */
const INNER_SPLITTER_OPTIONS = {
  KFold: ["KFold", "StratifiedKFold"],
  StratifiedKFold: ["KFold", "StratifiedKFold"],
  RepeatedKFold: ["KFold", "StratifiedKFold"],
  RepeatedStratifiedKFold: ["KFold", "StratifiedKFold"],
  GroupKFold: ["GroupKFold", "StratifiedGroupKFold"],
  StratifiedGroupKFold: ["GroupKFold", "StratifiedGroupKFold"],
  LeaveOneOut: ["Kfold", "StratifiedKFold"],
};

const DEFAULT_INNER_FOLDS = 2;

/**
 * Component for selecting nested cross-validation option with informational messages.
 * When nested CV is enabled, allows configuring the inner loop splitter and folds.
 *
 * @param {boolean} useNestedCV - Whether nested cross-validation is enabled
 * @param {function} onChange - Callback when checkbox state changes
 * @param {object} innerConfig - Inner loop configuration { splitterType, nSplits }
 * @param {function} onInnerConfigChange - Callback when inner config changes
 * @param {object} outerSplit - session.splits object from the parent session
 * @param {boolean} [disabled] - Whether to disable the checkbox
 */
function NestedCVSelector({
  useNestedCV,
  onChange,
  innerConfig,
  onInnerConfigChange,
  outerSplit,
  disabled = false,
}) {
  const { t } = useTranslation(["models", "common"]);

  const outerNSplits = outerSplit?.n_splits || 2;

  const compatibleInnerSplitters =
    INNER_SPLITTER_OPTIONS[outerSplit.splitter_name];

  const learnMoreLink = (
    <Link
      href="https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html"
      target="_blank"
      rel="noopener noreferrer"
      sx={{ color: "info.main", fontWeight: 600 }}
    >
      {t("common:learnMore")}
    </Link>
  );

  const handleInnerSplitterChange = (e) => {
    onInnerConfigChange({ ...innerConfig, splitterType: e.target.value });
  };

  const handleInnerFoldsChange = (e) => {
    const raw = e.target.value;
    if (raw === "" || isNaN(parseInt(raw, 10))) {
      // Allow empty while typing; onBlur will reset if still empty
      onInnerConfigChange({ ...innerConfig, nSplits: raw });
      return;
    }
    onInnerConfigChange({ ...innerConfig, nSplits: parseInt(raw, 10) });
  };

  const handleInnerFoldsBlur = () => {
    const current = innerConfig?.nSplits;
    const parsed = parseInt(current, 10);
    if (
      !current ||
      isNaN(parsed) ||
      parsed < 2 ||
      parsed > Math.min(outerNSplits, 20)
    ) {
      onInnerConfigChange({ ...innerConfig, nSplits: DEFAULT_INNER_FOLDS });
    }
  };

  const currentFolds = parseInt(innerConfig?.nSplits, 10);
  const showFoldsWarning =
    !isNaN(currentFolds) &&
    (currentFolds < 2 || currentFolds > Math.min(outerNSplits, 20));

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      <FormControlLabel
        control={
          <Checkbox
            checked={useNestedCV}
            onChange={(e) => onChange(e.target.checked)}
            disabled={disabled}
          />
        }
        label={t("models:label.nestedCrossValidation")}
      />

      <Alert severity="info" sx={{ py: 1.5, overflow: "hidden" }}>
        <Fade key={String(useNestedCV)} in timeout={{ enter: 350, exit: 0 }}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            <div>
              {useNestedCV
                ? t("models:message.processChosenNestedCV") + " "
                : t("models:message.processChosenNormalHPO")}
              {useNestedCV && learnMoreLink}
            </div>
            <Typography variant="body2" color="text.secondary">
              {useNestedCV
                ? t("models:message.computationalCostNestedCV")
                : t("models:message.computationalCostNormalHPO")}
            </Typography>
          </Box>
        </Fade>
      </Alert>

      <Collapse in={useNestedCV} unmountOnExit>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            p: 2,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 1,
            bgcolor: "background.default",
          }}
        >
          <Typography variant="subtitle2">
            {t("models:label.innerLoopConfiguration")}
          </Typography>

          {/* Outer loop — read only for reference */}
          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label={t("models:label.outerSplitter")}
              value={outerSplit.splitter_name}
              size="small"
              disabled
              fullWidth
              helperText={t("models:label.outerSplitterInherited")}
            />
            <TextField
              label={t("models:label.outerFolds")}
              value={outerNSplits}
              size="small"
              disabled
              sx={{ maxWidth: 120 }}
            />
          </Box>

          <Divider />

          {/* Inner loop — configurable */}
          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              select
              label={t("models:label.innerSplitter")}
              value={innerConfig?.splitterType || compatibleInnerSplitters[0]}
              onChange={handleInnerSplitterChange}
              size="small"
              fullWidth
            >
              {compatibleInnerSplitters.map((splitter) => (
                <MenuItem key={splitter} value={splitter}>
                  {splitter}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label={t("models:label.innerFolds")}
              type="number"
              value={innerConfig?.nSplits ?? DEFAULT_INNER_FOLDS}
              onChange={handleInnerFoldsChange}
              onBlur={handleInnerFoldsBlur}
              size="small"
              sx={{ width: 120, flexShrink: 0 }}
              inputProps={{ min: 2, max: Math.min(outerNSplits, 20) }}
            />
          </Box>

          {showFoldsWarning && (
            <Alert severity="warning" sx={{ py: 0.5 }}>
              {t("models:message.innerFoldsOutOfRange", {
                min: 2,
                max: 20,
                outerNSplits,
              })}
            </Alert>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}

NestedCVSelector.propTypes = {
  useNestedCV: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  innerConfig: PropTypes.shape({
    splitterType: PropTypes.string,
    nSplits: PropTypes.number,
  }).isRequired,
  onInnerConfigChange: PropTypes.func.isRequired,
  outerSplit: PropTypes.object,
  disabled: PropTypes.bool,
};

export default NestedCVSelector;
