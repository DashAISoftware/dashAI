import React, { useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Button,
  Chip,
  IconButton,
  Stack,
} from "@mui/material";
import { Add as AddIcon, Delete as DeleteIcon } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import AddSessionConverterDialog from "./AddSessionConverterDialog";

/**
 * Optional session step: configure converters (scalers, encoders, PCA,
 * imputers, etc.) to fit only on the training split and apply to the rest,
 * avoiding data leakage. Writes straight into `newExp.converters`; the
 * actual fit/transform runs once in SessionPreprocessingJob after the
 * session is created (see backend plan).
 */
function SelectConvertersStep({
  newExp,
  setNewExp,
  inputColumnNames,
  columnTypes,
}) {
  const { t } = useTranslation(["models", "common"]);
  const [dialogOpen, setDialogOpen] = useState(false);

  const converters = newExp.converters || [];

  const handleAddConverter = (converter) => {
    setNewExp((prev) => ({
      ...prev,
      converters: [...(prev.converters || []), converter],
    }));
  };

  const handleRemoveConverter = (index) => {
    setNewExp((prev) => ({
      ...prev,
      converters: (prev.converters || []).filter((_, i) => i !== index),
    }));
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        {t("models:label.sessionConverters")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("models:label.sessionConvertersDescription")}
      </Typography>

      {converters.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("models:label.noConvertersAdded")}
        </Typography>
      ) : (
        <Stack spacing={1} sx={{ mb: 2 }}>
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
                <Box
                  sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 0.5 }}
                >
                  {converter.columns.map((col) => (
                    <Chip key={col} label={col} size="small" />
                  ))}
                </Box>
              </Box>
              <IconButton
                size="small"
                onClick={() => handleRemoveConverter(index)}
                aria-label={t("common:remove")}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
        </Stack>
      )}

      <Button
        startIcon={<AddIcon />}
        variant="outlined"
        size="small"
        onClick={() => setDialogOpen(true)}
      >
        {t("models:button.addConverter")}
      </Button>

      <AddSessionConverterDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        inputColumns={inputColumnNames}
        columnTypes={columnTypes}
        onAddConverter={handleAddConverter}
      />
    </Box>
  );
}

SelectConvertersStep.propTypes = {
  newExp: PropTypes.shape({
    converters: PropTypes.array,
  }).isRequired,
  setNewExp: PropTypes.func.isRequired,
  inputColumnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  columnTypes: PropTypes.object,
};

export default SelectConvertersStep;
