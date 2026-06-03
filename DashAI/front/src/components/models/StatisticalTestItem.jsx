import React, { useMemo } from "react";
import PropTypes from "prop-types";
import { Box, Card, CardContent, Typography, Chip } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

function StatisticalTestItem({ test, isSelected, onSelect, numberOfRuns }) {
  const theme = useTheme();
  const { i18n } = useTranslation();

  // Determinar requisitos mínimos basado en metadata
  const minRuns = test.metadata?.min_runs || 2;

  const isAvailable = numberOfRuns >= minRuns;

  // Obtener descripción en el idioma actual
  const getDescription = useMemo(() => {
    if (
      test.metadata?.description &&
      typeof test.metadata.description === "object"
    ) {
      // Obtener el código de idioma (e.g., 'en' from 'en-US')
      const langCode = i18n.language?.split("-")[0] || "en";
      return (
        test.metadata.description[langCode] ||
        test.metadata.description["en"] ||
        "No description"
      );
    }
    return test.description || "No description";
  }, [test, i18n.language]);

  return (
    <Card
      onClick={() => isAvailable && onSelect(test)}
      sx={{
        mb: 1,
        cursor: isAvailable ? "pointer" : "not-allowed",
        opacity: isAvailable ? 1 : 0.5,
        backgroundColor: isSelected ? theme.palette.action.selected : "inherit",
        border: isSelected
          ? `2px solid ${theme.palette.primary.main}`
          : `1px solid ${theme.palette.divider}`,
        transition: "all 0.2s ease",
        "&:hover": {
          backgroundColor: isAvailable ? theme.palette.action.hover : "inherit",
          transform: isAvailable ? "translateX(4px)" : "none",
        },
      }}
    >
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              variant="subtitle2"
              sx={{
                fontWeight: 600,
                color: isAvailable ? "text.primary" : "text.disabled",
              }}
            >
              {test.metadata?.name}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: isAvailable ? "text.secondary" : "text.disabled",
                display: "block",
                mt: 0.5,
              }}
            >
              {getDescription}
            </Typography>
          </Box>
          {!isAvailable && (
            <Chip
              label={`Min: ${minRuns}+`}
              size="small"
              variant="outlined"
              sx={{ flexShrink: 0 }}
            />
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

StatisticalTestItem.propTypes = {
  test: PropTypes.shape({
    name: PropTypes.string.isRequired,
    display_name: PropTypes.string,
    description: PropTypes.string,
    metadata: PropTypes.object,
  }).isRequired,
  isSelected: PropTypes.bool.isRequired,
  onSelect: PropTypes.func.isRequired,
  numberOfRuns: PropTypes.number.isRequired,
};

export default StatisticalTestItem;
