import React, { useEffect } from "react";
import PropTypes from "prop-types";
import {
  Box,
  FormControlLabel,
  Radio,
  RadioGroup,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";

const SPLITS = ["train", "validation", "test"];

/**
 * First step of the report creator: pick the split.
 *
 * The split is a real choice rather than a default because a report
 * describes exactly one prediction set. Reading the same report on train
 * and on test side by side is how overfitting shows up, and that comparison
 * only exists if each split is its own report.
 */
export default function SelectSplitStep({
  newReport,
  setNewReport,
  setNextEnabled,
}) {
  const { t } = useTranslation(["reports"]);

  useEffect(() => {
    setNextEnabled(Boolean(newReport.split));
  }, [newReport.split, setNextEnabled]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          {t("reports:label.split")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("reports:message.splitHelp")}
        </Typography>
        <RadioGroup
          value={newReport.split}
          onChange={(event) =>
            setNewReport((prev) => ({ ...prev, split: event.target.value }))
          }
        >
          {SPLITS.map((split) => (
            <FormControlLabel
              key={split}
              value={split}
              control={<Radio />}
              label={t(`reports:label.split_${split}`)}
            />
          ))}
        </RadioGroup>
      </Box>
    </Box>
  );
}

SelectSplitStep.propTypes = {
  newReport: PropTypes.shape({
    split: PropTypes.string,
  }).isRequired,
  setNewReport: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};
