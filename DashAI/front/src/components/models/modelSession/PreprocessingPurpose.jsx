import React, { useState } from "react";
import PropTypes from "prop-types";
import { Box, Button, Collapse, Stack, Typography } from "@mui/material";
import { ExpandMore } from "@mui/icons-material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { roleColors } from "./SplitPreview";
import { SPLIT_ROLES } from "../../../utils/splitPreview";
import { STRATEGY_KINDS } from "../../../utils/splitsPayload";

const REASONS = [
  "compatibility",
  "cleaning",
  "honestMetrics",
  "performance",
  "consistency",
];

function PartitionChip({ color, label }) {
  return (
    <Box
      component="span"
      sx={{
        bgcolor: color,
        color: "common.white",
        px: 1,
        py: 0.25,
        borderRadius: 1,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </Box>
  );
}

PartitionChip.propTypes = {
  color: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
};

/**
 * Why the session's preprocessing is worth turning on, folded under the
 * switch so the step stays short for whoever already knows.
 *
 * The honest-metrics reason carries a small diagram in the partition
 * colors of SplitPreview: the training rows fit the preprocessing and the
 * rest only receive it. Under cross-validation there is no fixed
 * validation or test partition, so it speaks of each fold instead.
 */
function PreprocessingPurpose({ strategyKind }) {
  const { t } = useTranslation(["models", "common"]);
  const theme = useTheme();
  const colors = roleColors(theme);
  const [open, setOpen] = useState(false);
  const isCv = strategyKind === STRATEGY_KINDS.CV;

  const diagram = (
    <Stack
      direction="row"
      spacing={1}
      alignItems="center"
      flexWrap="wrap"
      useFlexGap
      sx={{ my: 1 }}
    >
      <PartitionChip
        color={colors[SPLIT_ROLES.TRAIN]}
        label={t("common:train")}
      />
      <span>{t("models:preprocessingPurpose.diagramFits")}</span>
      {isCv ? (
        <PartitionChip
          color={colors[SPLIT_ROLES.VALIDATION]}
          label={t("models:preprocessingPurpose.diagramFoldEvaluation")}
        />
      ) : (
        <>
          <PartitionChip
            color={colors[SPLIT_ROLES.VALIDATION]}
            label={t("common:validation")}
          />
          <PartitionChip
            color={colors[SPLIT_ROLES.TEST]}
            label={t("common:test")}
          />
        </>
      )}
      <span>
        {t(
          isCv
            ? "models:preprocessingPurpose.diagramReceivesOne"
            : "models:preprocessingPurpose.diagramReceives",
        )}
      </span>
    </Stack>
  );

  return (
    <Box>
      <Button
        size="small"
        onClick={() => setOpen((prev) => !prev)}
        endIcon={
          <ExpandMore
            sx={{
              transform: open ? "rotate(180deg)" : "none",
              transition: "transform 0.2s",
            }}
          />
        }
        sx={{ px: 0, textTransform: "none" }}
      >
        {t("models:preprocessingPurpose.toggle")}
      </Button>
      <Collapse in={open}>
        <Stack
          spacing={1}
          sx={{ mt: 1, pl: 2, borderLeft: 2, borderColor: "divider" }}
        >
          {REASONS.map((reason) => (
            <Box key={reason}>
              <Typography variant="body2">
                <b>{t(`models:preprocessingPurpose.${reason}Title`)}</b>{" "}
                {t(`models:preprocessingPurpose.${reason}`)}
              </Typography>
              {reason === "honestMetrics" && (
                <>
                  <Typography variant="body2" component="div">
                    {diagram}
                  </Typography>
                  <Typography variant="body2">
                    {t(
                      isCv
                        ? "models:preprocessingPurpose.honestMetricsCvOutcome"
                        : "models:preprocessingPurpose.honestMetricsOutcome",
                    )}
                  </Typography>
                </>
              )}
            </Box>
          ))}
        </Stack>
      </Collapse>
    </Box>
  );
}

PreprocessingPurpose.propTypes = {
  strategyKind: PropTypes.string,
};

export default PreprocessingPurpose;
