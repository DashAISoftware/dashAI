import React from "react";
import { Box, Button, IconButton, Typography } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import StepperNavigationFooter from "../shared/StepperNavigationFooter";

// Half-diagonal of the rotated square = visible arrow protrusion in px
const ARROW = 8;

function getArrowSx(placement) {
  if (!placement || placement === "center" || placement === "auto") return null;
  const base = {
    position: "absolute",
    width: ARROW * 2,
    height: ARROW * 2,
    backgroundColor: "#fff",
    transform: "rotate(45deg)",
    // lower z-index so it sits behind the tooltip content but is part of the
    // parent's filter stacking context
    zIndex: 0,
  };
  if (placement.startsWith("top"))
    return { ...base, bottom: -ARROW, left: `calc(50% - ${ARROW}px)` };
  if (placement.startsWith("bottom"))
    return { ...base, top: -ARROW, left: `calc(50% - ${ARROW}px)` };
  if (placement.startsWith("left"))
    return { ...base, right: -ARROW, top: `calc(50% - ${ARROW}px)` };
  if (placement.startsWith("right"))
    return { ...base, left: -ARROW, top: `calc(50% - ${ARROW}px)` };
  return null;
}

export const CustomTooltip = ({
  index,
  step,
  backProps,
  closeProps,
  primaryProps,
  skipProps,
  tooltipProps,
  size,
  isLastStep,
}) => {
  const { t } = useTranslation(["common"]);
  const theme = useTheme();
  const isInteractive = step.isInteractive;
  const arrowSx = getArrowSx(step.placement);

  return (
    <Box
      {...tooltipProps}
      sx={{
        backgroundColor: "#fff",
        borderRadius: "8px",
        // drop-shadow on the Box includes the child arrow in its shape,
        // so the shadow follows the combined silhouette with no visible seam.
        filter: "drop-shadow(0 3px 10px rgba(0, 0, 0, 0.18))",
        maxWidth: "30ch",
        padding: "20px",
        position: "relative",
        overflow: "visible",
        zIndex: 1,
      }}
    >
      {/* Custom arrow — part of the Box's filter context */}
      {arrowSx && <Box sx={arrowSx} />}

      {/* Close button */}
      <IconButton
        {...closeProps}
        size="small"
        sx={{
          position: "absolute",
          top: 8,
          right: 8,
          color: "#999",
          zIndex: 2,
          "&:hover": { color: "#333" },
        }}
      >
        <CloseIcon fontSize="small" />
      </IconButton>

      {/* Step counter */}
      <Typography
        variant="overline"
        sx={{
          color: theme.palette.primary.main,
          fontWeight: 700,
          letterSpacing: 1.5,
          lineHeight: 1,
          display: "block",
          mb: 1,
          zIndex: 2,
          position: "relative",
        }}
      >
        {t("common:step")} {index + 1} / {size}
      </Typography>

      {/* Content */}
      <Box
        sx={{
          fontSize: "14px",
          lineHeight: "1.6",
          color: "#333",
          pr: 2,
          position: "relative",
          zIndex: 2,
          "& h3": {
            fontSize: "16px",
            fontWeight: "bold",
            marginBottom: "8px",
            marginTop: 0,
            color: "#333",
          },
          "& p": { marginBottom: "8px", marginTop: 0 },
          "& ul": { marginBottom: "8px", marginTop: "8px" },
          "& li": { marginBottom: "4px" },
          "& strong": { fontWeight: 600, color: "#000" },
        }}
      >
        {step.content}
      </Box>

      {/* Footer: Skip (left) | Back + Next (right) */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mt: 1,
          position: "relative",
          zIndex: 2,
        }}
      >
        <Box>
          {!isLastStep && (
            <Button
              {...skipProps}
              variant="text"
              size="small"
              sx={{
                color: "#999",
                textTransform: "none",
                fontSize: "12px",
                "&:hover": { backgroundColor: "rgba(0,0,0,0.04)" },
              }}
            >
              {t("common:skipTour")}
            </Button>
          )}
        </Box>

        <StepperNavigationFooter
          onBack={
            index > 0 && !step.disableBackButton
              ? backProps?.onClick
              : undefined
          }
          onNext={!isInteractive ? primaryProps?.onClick : undefined}
          showBack={index > 0 && !step.disableBackButton}
          showNext={!isInteractive}
          nextLabel={isLastStep ? t("common:finish") : t("common:next")}
          sx={{ mt: 0, pt: 0, borderTop: 0 }}
        />
      </Box>
    </Box>
  );
};
