import React from "react";
import { Box, Button, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

export const CustomTooltip = ({
  continuous,
  index,
  step,
  backProps,
  primaryProps,
  skipProps,
  tooltipProps,
  size,
  isLastStep,
}) => {
  const { t } = useTranslation(["common"]);
  const theme = useTheme();
  const isInteractive = step.isInteractive;

  return (
    <Box
      {...tooltipProps}
      sx={{
        backgroundColor: "#fff",
        borderRadius: "8px",
        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.15)",
        maxWidth: step.maxWidth || "380px",
        padding: "20px",
      }}
    >
      <Box
        sx={{
          marginBottom: "16px",
          fontSize: "14px",
          lineHeight: "1.6",
          color: "#333",
          "& h3": {
            fontSize: "22px",
            fontWeight: "bold",
            marginBottom: "8px",
            marginTop: 0,
            color: "#333",
          },
          "& p": {
            marginBottom: "8px",
            marginTop: 0,
          },
          "& ul": {
            marginBottom: "8px",
            marginTop: "8px",
          },
          "& li": {
            marginBottom: "4px",
          },
          "& strong": {
            fontWeight: 600,
            color: "#000",
          },
        }}
      >
        {step.content}
      </Box>

      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "16px",
        }}
      >
        <Box>
          {index > 0 && !step.disableBackButton && (
            <Button
              {...backProps}
              sx={{
                color: "#666",
                textTransform: "none",
                "&:hover": {
                  backgroundColor: "rgba(0, 0, 0, 0.04)",
                },
              }}
            >
              {t("common:back")}
            </Button>
          )}
        </Box>{" "}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          {!isLastStep && (
            <Button
              {...skipProps}
              sx={{
                color: "#999",
                fontSize: "12px",
                textTransform: "none",
                "&:hover": {
                  backgroundColor: "rgba(0, 0, 0, 0.04)",
                },
              }}
            >
              {t("common:skipTour")}
            </Button>
          )}

          {isInteractive ? (
            <Typography
              variant="caption"
              sx={{
                color: "#999",
                padding: "8px 16px",
                backgroundColor: "rgba(0, 0, 0, 0.04)",
                borderRadius: "4px",
              }}
            >
              {index + 1} of {size}
            </Typography>
          ) : (
            <Button
              {...primaryProps}
              sx={{
                backgroundColor: theme.palette.primary.main,
                color: theme.palette.primary.contrastText,
                borderRadius: "4px",
                padding: "8px 16px",
                fontSize: "14px",
                textTransform: "none",
                "&:hover": {
                  backgroundColor: theme.palette.primary.dark,
                },
                display: "flex",
                gap: 2,
              }}
            >
              {isLastStep ? t("common:finish") : t("common:next")}
              {continuous && (
                <Typography
                  component="span"
                  variant="body2"
                  sx={{
                    opacity: 0.8,
                    ml: 1,
                  }}
                >
                  ({index + 1}/{size})
                </Typography>
              )}
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
};
