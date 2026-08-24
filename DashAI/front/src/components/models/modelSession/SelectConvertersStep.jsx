import React from "react";
import PropTypes from "prop-types";
import { Box, Typography, Chip, IconButton, Stack } from "@mui/material";
import { Delete as DeleteIcon } from "@mui/icons-material";
import { useTranslation } from "react-i18next";

/**
 * List of the session's configured converters (scalers, encoders, PCA,
 * imputers, etc.), each fit only on the training split and applied to the
 * rest — see SessionPreprocessingJob on the backend. Adding happens from
 * the preprocessing step's sidebar (SessionConvertersRightBar); this
 * component only renders what's already in `newExp.converters` and lets
 * the user remove one.
 */
function SelectConvertersStep({ newExp, setNewExp }) {
  const { t } = useTranslation(["models", "common"]);
  const converters = newExp.converters || [];

  const handleRemoveConverter = (index) => {
    setNewExp((prev) => ({
      ...prev,
      converters: (prev.converters || []).filter((_, i) => i !== index),
    }));
  };

  if (converters.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {t("models:label.noConvertersAdded")}
      </Typography>
    );
  }

  return (
    <Stack spacing={1}>
      {converters.map((converter, index) => (
        <Box
          key={`${converter.converter}-${index}`}
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            p: 2,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 1,
          }}
        >
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {converter.converter}
            </Typography>
            <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 0.5 }}>
              {converter.columns.map((col) => (
                <Chip key={col} label={col} size="small" />
              ))}
            </Box>
          </Box>
          <IconButton
            size="small"
            color="error"
            onClick={() => handleRemoveConverter(index)}
            aria-label={t("common:remove")}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      ))}
    </Stack>
  );
}

SelectConvertersStep.propTypes = {
  newExp: PropTypes.shape({
    converters: PropTypes.array,
  }).isRequired,
  setNewExp: PropTypes.func.isRequired,
};

export default SelectConvertersStep;
