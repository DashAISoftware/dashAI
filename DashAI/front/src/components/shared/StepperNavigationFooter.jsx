import { Box, Button, CircularProgress } from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";

/**
 * Reusable navigation footer component for steppers, wizards, and multi-step flows.
 * Provides consistent styling with sticky positioning and always-visible buttons.
 *
 * @param {function} onBack - Callback when back button is clicked
 * @param {function} onNext - Callback when next/save button is clicked
 * @param {boolean} backDisabled - Disable back button
 * @param {boolean} nextDisabled - Disable next button
 * @param {string} backLabel - Custom back button label (default: "back")
 * @param {string} nextLabel - Custom next button label (default: "next")
 * @param {boolean} showBack - Show back button (default: true)
 * @param {boolean} showNext - Show next button (default: true)
 * @param {string} variant - Next button variant: "next" or "save" (default: "next")
 * @param {boolean} loading - Show loading state in next button
 * @param {string} sx - Additional MUI sx styles for the footer
 */
export default function StepperNavigationFooter({
  onBack,
  onNext,
  backDisabled = false,
  nextDisabled = false,
  backLabel,
  nextLabel,
  showBack = true,
  showNext = true,
  variant = "next",
  loading = false,
  sx = {},
}) {
  const { t } = useTranslation(["common"]);

  const finalBackLabel = backLabel ?? t("common:back");
  const finalNextLabel =
    nextLabel ?? (variant === "save" ? t("common:save") : t("common:next"));

  return (
    <Box
      sx={{
        mt: "auto",
        borderTop: 1,
        borderColor: "divider",
        flexShrink: 0,
        display: "flex",
        justifyContent: "flex-end",
        gap: 1,
        pt: 2,
        ...sx,
      }}
    >
      {showBack && onBack && (
        <Button
          variant="outlined"
          onClick={onBack}
          disabled={backDisabled || loading}
        >
          {finalBackLabel}
        </Button>
      )}
      {showNext && onNext && (
        <Button
          variant="contained"
          onClick={onNext}
          disabled={nextDisabled || loading}
          sx={{
            position: "relative",
          }}
        >
          {loading && (
            <CircularProgress
              size={20}
              sx={{
                position: "absolute",
                left: "50%",
                marginLeft: "-10px",
              }}
            />
          )}
          <span
            style={{
              visibility: loading ? "hidden" : "visible",
            }}
          >
            {finalNextLabel}
          </span>
        </Button>
      )}
    </Box>
  );
}

StepperNavigationFooter.propTypes = {
  onBack: PropTypes.func,
  onNext: PropTypes.func,
  backDisabled: PropTypes.bool,
  nextDisabled: PropTypes.bool,
  backLabel: PropTypes.string,
  nextLabel: PropTypes.string,
  showBack: PropTypes.bool,
  showNext: PropTypes.bool,
  variant: PropTypes.oneOf(["next", "save"]),
  loading: PropTypes.bool,
  sx: PropTypes.object,
};
