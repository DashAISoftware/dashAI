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
 * First step of the diagnostic creator: pick the split.
 *
 * The split is a real choice rather than a default because a diagnostic
 * describes exactly one prediction set. Reading the same diagnostic on train
 * and on test side by side is how overfitting shows up, and that comparison
 * only exists if each split is its own diagnostic.
 */
export default function SelectSplitStep({
  newDiagnostic,
  setNewDiagnostic,
  setNextEnabled,
}) {
  const { t } = useTranslation(["diagnostics"]);

  useEffect(() => {
    setNextEnabled(Boolean(newDiagnostic.split));
  }, [newDiagnostic.split, setNextEnabled]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          {t("diagnostics:label.split")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("diagnostics:message.splitHelp")}
        </Typography>
        <RadioGroup
          value={newDiagnostic.split}
          onChange={(event) =>
            setNewDiagnostic((prev) => ({ ...prev, split: event.target.value }))
          }
        >
          {SPLITS.map((split) => (
            <FormControlLabel
              key={split}
              value={split}
              control={<Radio />}
              label={t(`diagnostics:label.split_${split}`)}
            />
          ))}
        </RadioGroup>
      </Box>
    </Box>
  );
}

SelectSplitStep.propTypes = {
  newDiagnostic: PropTypes.shape({
    split: PropTypes.string,
  }).isRequired,
  setNewDiagnostic: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};
