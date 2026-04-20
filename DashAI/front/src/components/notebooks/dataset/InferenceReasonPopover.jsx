import { useState } from "react";
import {
  Box,
  IconButton,
  Popover,
  Typography,
  Chip,
  Divider,
  Stack,
} from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { useTranslation } from "react-i18next";

const RULE_DESCRIPTIONS = {
  boolean_always_categorical: "datasets:inferenceReason.rule.boolean",
  date_type_excluded: "datasets:inferenceReason.rule.dateExcluded",
  date_detected_mapped_to_text:
    "datasets:inferenceReason.rule.dateMappedToText",
  string_looks_like_date: "datasets:inferenceReason.rule.stringLooksLikeDate",
  too_many_unique_values: "datasets:inferenceReason.rule.tooManyUnique",
  unique_ratio_above_threshold:
    "datasets:inferenceReason.rule.uniqueRatioAbove",
  string_too_long: "datasets:inferenceReason.rule.stringTooLong",
  string_high_length_variance:
    "datasets:inferenceReason.rule.stringHighVariance",
  integer_all_unique: "datasets:inferenceReason.rule.integerAllUnique",
  integer_sequential_range:
    "datasets:inferenceReason.rule.integerSequentialRange",
  integer_dense_small_range:
    "datasets:inferenceReason.rule.integerDenseSmallRange",
  float_has_decimals: "datasets:inferenceReason.rule.floatHasDecimals",
  low_cardinality: "datasets:inferenceReason.rule.lowCardinality",
  ml_classifier_categorical:
    "datasets:inferenceReason.rule.mlClassifierCategorical",
  ml_classifier_not_categorical:
    "datasets:inferenceReason.rule.mlClassifierNotCategorical",
  empty_column: "datasets:inferenceReason.rule.emptyColumn",
  unsupported_base_type: "datasets:inferenceReason.rule.unsupportedBaseType",
  unknown: "datasets:inferenceReason.rule.unknown",
};

export default function InferenceReasonPopover({ columnName, reason }) {
  const { t } = useTranslation(["datasets", "common"]);
  const [anchorEl, setAnchorEl] = useState(null);

  if (!reason) return null;

  const open = Boolean(anchorEl);
  const ruleKey = RULE_DESCRIPTIONS[reason.rule] || RULE_DESCRIPTIONS.unknown;

  const ratioPct = (reason.unique_ratio * 100).toFixed(2);
  const maxRatioPct = (reason.thresholds?.max_unique_ratio * 100).toFixed(1);

  const SKIP_THRESHOLD_RULES = new Set([
    "date_type_excluded",
    "date_detected_mapped_to_text",
    "string_looks_like_date",
    "empty_column",
    "unsupported_base_type",
    "float_has_decimals",
  ]);
  const showCategoricalThreshold = !SKIP_THRESHOLD_RULES.has(reason.rule);

  return (
    <>
      <IconButton
        size="small"
        onClick={(e) => {
          e.stopPropagation();
          setAnchorEl(e.currentTarget);
        }}
        sx={{ p: 0.25, ml: 0.5 }}
        aria-label={t("datasets:inferenceReason.openExplanation")}
      >
        <InfoOutlinedIcon sx={{ fontSize: "0.95rem" }} />
      </IconButton>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        slotProps={{ paper: { sx: { p: 2, maxWidth: 360 } } }}
      >
        <Stack spacing={1}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            {t("datasets:inferenceReason.title", { column: columnName })}
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              size="small"
              label={reason.final_type}
              color={reason.is_categorical ? "warning" : "primary"}
            />
            <Typography variant="caption" color="text.secondary">
              {t("datasets:inferenceReason.baseType", {
                type: reason.inferred_base_type,
              })}
            </Typography>
          </Box>
          <Typography variant="body2">
            {t(ruleKey, { baseType: reason.inferred_base_type })}
          </Typography>
          <Divider flexItem />
          <Box>
            <Typography variant="caption" color="text.secondary">
              {t("datasets:inferenceReason.stats")}
            </Typography>
            <Typography variant="body2">
              {t("datasets:inferenceReason.uniqueCount", {
                count: reason.unique_count,
                total: reason.total_count,
              })}
            </Typography>
            <Typography variant="body2">
              {showCategoricalThreshold
                ? t("datasets:inferenceReason.uniqueRatio", {
                    ratio: ratioPct,
                    threshold: maxRatioPct,
                  })
                : t("datasets:inferenceReason.uniqueRatioNoThreshold", {
                    ratio: ratioPct,
                  })}
            </Typography>
            {reason.string_length && (
              <Typography variant="body2">
                {t("datasets:inferenceReason.stringLength", {
                  mean: reason.string_length.mean,
                  std: reason.string_length.std,
                })}
              </Typography>
            )}
          </Box>
          {reason.sample_values?.length > 0 && (
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("datasets:inferenceReason.sampleValues")}
              </Typography>
              <Box
                sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}
              >
                {reason.sample_values.map((v, i) => (
                  <Chip
                    key={i}
                    size="small"
                    label={String(v)}
                    variant="outlined"
                  />
                ))}
              </Box>
            </Box>
          )}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontStyle: "italic" }}
          >
            {t("datasets:inferenceReason.canChangeHint")}
          </Typography>
        </Stack>
      </Popover>
    </>
  );
}
