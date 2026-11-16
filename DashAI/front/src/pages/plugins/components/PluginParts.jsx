import React from "react";
import PropTypes from "prop-types";
import { Box, Tooltip, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import GppGoodOutlinedIcon from "@mui/icons-material/GppGoodOutlined";
import { useTranslation } from "react-i18next";
import { trustOf, trustText } from "../pluginUtils";

export function VerifiedBadge({ withLabel = false }) {
  const { t } = useTranslation(["plugins"]);
  const icon = (
    <GppGoodOutlinedIcon sx={{ fontSize: 16, color: "primary.main" }} />
  );
  if (!withLabel) {
    return (
      <Tooltip title={t("plugins:label.official")}>
        <Box component="span" sx={{ display: "inline-flex" }}>
          {icon}
        </Box>
      </Tooltip>
    );
  }
  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.5,
        px: 1,
        py: 0.25,
        borderRadius: 0.5,
        bgcolor: (theme) => alpha(theme.palette.primary.main, 0.1),
        color: "primary.main",
        fontSize: 12,
      }}
    >
      {icon}
      {t("plugins:label.officialBadge")}
    </Box>
  );
}
VerifiedBadge.propTypes = { withLabel: PropTypes.bool };

export function TypeChip({ type }) {
  const theme = useTheme();
  return (
    <Box
      component="span"
      sx={{
        ...theme.typography.statusBadge,
        lineHeight: 1,
        px: "7px",
        py: "2px",
        borderRadius: "2px",
        border: `1px solid ${theme.palette.divider}`,
        background: theme.palette.background.default,
        color: theme.palette.text.primary,
        whiteSpace: "nowrap",
      }}
    >
      {type}
    </Box>
  );
}
TypeChip.propTypes = { type: PropTypes.string.isRequired };

export function SectionLabel({ children, sx }) {
  const theme = useTheme();
  return (
    <Typography
      component="div"
      sx={{
        ...theme.typography.sectionLabel,
        color: "text.secondary",
        mb: 1,
        ...sx,
      }}
    >
      {children}
    </Typography>
  );
}
SectionLabel.propTypes = { children: PropTypes.node, sx: PropTypes.object };

export function TrustNotice({ trust, before = false, children }) {
  const { t } = useTranslation(["plugins"]);
  const { Icon, color } = trustOf(trust.trust_tier);
  return (
    <Box
      sx={{
        display: "flex",
        gap: 1.5,
        p: 2,
        borderRadius: 1,
        border: `1px solid ${alpha(color, 0.45)}`,
        bgcolor: alpha(color, 0.08),
      }}
    >
      <Icon sx={{ color, fontSize: 18, mt: 0.25 }} />
      <Box sx={{ minWidth: 0 }}>
        <Typography sx={{ color, fontWeight: 600, fontSize: 14 }}>
          {t(trustText(trust, "label"))}
        </Typography>
        <Typography sx={{ fontSize: 13, mt: 0.5 }}>
          {t(trustText(trust, before ? "textBefore" : "text"))}
        </Typography>
        {children}
      </Box>
    </Box>
  );
}
TrustNotice.propTypes = {
  trust: PropTypes.shape({
    trust_level: PropTypes.string,
    trust_tier: PropTypes.string,
  }).isRequired,
  before: PropTypes.bool,
  children: PropTypes.node,
};

export const filledRows = (rows) =>
  rows.filter(
    ({ value }) => value !== null && value !== undefined && value !== "",
  );

export function InfoRows({ rows }) {
  const shown = filledRows(rows);
  return (
    <Box
      component="dl"
      sx={{
        display: "grid",
        gridTemplateColumns: "max-content minmax(0, 1fr)",
        columnGap: 3,
        rowGap: 1,
        m: 0,
      }}
    >
      {shown.map(({ label, value, mono }) => (
        <React.Fragment key={label}>
          <Typography
            component="dt"
            sx={{ fontSize: 13, color: "text.secondary" }}
          >
            {label}
          </Typography>
          <Typography
            component="dd"
            sx={{
              m: 0,
              fontSize: mono ? 12 : 13,
              fontFamily: mono ? '"Geist Mono", monospace' : undefined,
              wordBreak: "break-all",
            }}
          >
            {value}
          </Typography>
        </React.Fragment>
      ))}
    </Box>
  );
}
InfoRows.propTypes = {
  rows: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.node,
      mono: PropTypes.bool,
    }),
  ).isRequired,
};
