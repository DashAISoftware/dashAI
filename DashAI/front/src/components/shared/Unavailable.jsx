import React from "react";
import PropTypes from "prop-types";
import { Alert, Box, Button, Chip, Tooltip } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { unavailableText } from "../../utils/componentAvailability";

const missingShape = PropTypes.arrayOf(
  PropTypes.shape({ name: PropTypes.string, reason: PropTypes.string }),
);

// "Unavailable" on a saved record whose component is missing; the tooltip
// says which component and which plugin.
export function UnavailableChip({ missing }) {
  const { t } = useTranslation(["plugins"]);
  if (!missing.length) return null;
  return (
    <Tooltip title={unavailableText(t, missing)}>
      <Chip
        size="small"
        color="warning"
        variant="outlined"
        label={t("plugins:unavailable.chip")}
      />
    </Tooltip>
  );
}

UnavailableChip.propTypes = { missing: missingShape.isRequired };

// Why a view is read-only and the way back: the Plugins page, where the user
// enables, fixes or reinstalls it (the text already names the plugin).
export function UnavailableNotice({ missing, sx }) {
  const { t } = useTranslation(["plugins"]);
  if (!missing.length) return null;
  return (
    <Alert severity="warning" sx={sx}>
      {unavailableText(t, missing)} {t("plugins:unavailable.readOnly")}
      {/* Under the text, so it fits the narrow side bars too. */}
      <Box sx={{ mt: 1 }}>
        <Button
          component={RouterLink}
          to="/app/plugins"
          color="inherit"
          size="small"
          variant="outlined"
        >
          {t("plugins:unavailable.goToPlugins")}
        </Button>
      </Box>
    </Alert>
  );
}

UnavailableNotice.propTypes = {
  missing: missingShape.isRequired,
  sx: PropTypes.object,
};
