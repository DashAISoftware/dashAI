import React from "react";
import { Box, IconButton, Tooltip, Typography, useTheme } from "@mui/material";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { useTranslation } from "react-i18next";

/**
 * Displays required and optional placeholders with icons and a "+" button
 * to insert each placeholder into the prompt template textarea.
 */
export default function PlaceholdersList({
  required = [],
  optional = [],
  descriptions = {},
  template = "",
  onInsertPlaceholder,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["generative"]);
  const optionalOnly = optional.filter((ph) => !required.includes(ph));

  const renderRow = (ph, isRequired) => {
    const isPresent = template.includes(ph);
    return (
      <Box
        component="li"
        key={ph}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.5,
        }}
      >
        {isPresent ? (
          <CheckCircleIcon
            fontSize="small"
            color="success"
            sx={{ flexShrink: 0 }}
          />
        ) : isRequired ? (
          <WarningAmberIcon
            fontSize="small"
            color="error"
            sx={{ flexShrink: 0 }}
          />
        ) : (
          <RadioButtonUncheckedIcon
            fontSize="small"
            color="secondary"
            sx={{ flexShrink: 0 }}
          />
        )}

        {onInsertPlaceholder && (
          <Tooltip
            title={t("generative:rag.placeholders.insert", {
              placeholder: ph,
            })}
            placement="top"
          >
            <IconButton
              size="small"
              onClick={() => onInsertPlaceholder(ph)}
              aria-label={t("generative:rag.placeholders.insert", {
                placeholder: ph,
              })}
              sx={{
                p: 0.25,
                color: "primary.main",
                "@media (hover: hover)": {
                  "&:hover": { backgroundColor: "action.hover" },
                },
              }}
            >
              <AddCircleOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}

        <Typography
          component="code"
          variant="body2"
          sx={{
            fontFamily: theme.typography.code.fontFamily,
          }}
        >
          {ph}
        </Typography>

        {descriptions[ph] && (
          <Tooltip title={descriptions[ph]} placement="right">
            <HelpOutlineIcon
              fontSize="small"
              color="action"
              sx={{ cursor: "pointer", flexShrink: 0 }}
            />
          </Tooltip>
        )}
      </Box>
    );
  };

  return (
    <Box>
      <Typography variant="subtitle2" component="h3" sx={{ mb: 1 }}>
        {t("generative:rag.placeholders.title")}
      </Typography>
      <Box
        component="ul"
        sx={{
          listStyle: "none",
          m: 0,
          p: 0,
          display: "flex",
          flexDirection: "column",
          gap: 0.5,
        }}
      >
        {required.map((ph) => renderRow(ph, true))}
      </Box>

      {optionalOnly.length > 0 && (
        <>
          <Typography
            variant="subtitle2"
            component="h3"
            sx={{ mt: 1.5, mb: 1 }}
          >
            {t("generative:rag.placeholders.optionalTitle")}
          </Typography>
          <Box
            component="ul"
            sx={{
              listStyle: "none",
              m: 0,
              p: 0,
              display: "flex",
              flexDirection: "column",
              gap: 0.5,
            }}
          >
            {optionalOnly.map((ph) => renderRow(ph, false))}
          </Box>
        </>
      )}
    </Box>
  );
}
