import Breadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import IconButton from "@mui/material/IconButton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import PropTypes from "prop-types";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

/**
 * Breadcrumbs for the dataset export flow.
 *
 * Always starts with "Data / Export"; the steps after the platform pass their
 * own crumbs. The last crumb renders as plain text (current page).
 *
 * @param {Array<{label: string, onClick?: function}>} [crumbs] - Crumbs after "Export".
 * @param {function} [onBack] - Back-button handler. Defaults to the Data module.
 */
export default function ExportBreadcrumbs({ crumbs = [], onBack }) {
  const navigate = useNavigate();
  const { t } = useTranslation(["export", "common"]);

  const resolvedCrumbs = [
    { label: t("common:data"), onClick: () => navigate("/app/data") },
    {
      label: t("export:title"),
      onClick: crumbs.length ? () => navigate("/app/data/export") : undefined,
    },
    ...crumbs,
  ];

  const handleBack = onBack ?? (() => navigate("/app/data"));

  return (
    <Box
      sx={{
        mb: 4,
        minHeight: "24px",
        display: "flex",
        alignItems: "center",
        gap: 2,
      }}
    >
      <IconButton
        onClick={handleBack}
        size="small"
        sx={{
          color: "text.secondary",
          "&:hover": { color: "primary.main", backgroundColor: "action.hover" },
        }}
        aria-label={t("common:back")}
      >
        <ArrowBackIcon fontSize="small" />
      </IconButton>
      <Breadcrumbs
        aria-label="breadcrumb"
        sx={{ minHeight: "24px", display: "flex", alignItems: "center" }}
      >
        {resolvedCrumbs.map((crumb, index) => {
          const isLast = index === resolvedCrumbs.length - 1;
          if (isLast || !crumb.onClick) {
            return (
              <Typography key={index} color="text.primary">
                {crumb.label}
              </Typography>
            );
          }
          return (
            <Link
              key={index}
              underline="hover"
              color="inherit"
              component="button"
              onClick={crumb.onClick}
              sx={{ cursor: "pointer" }}
            >
              {crumb.label}
            </Link>
          );
        })}
      </Breadcrumbs>
    </Box>
  );
}

ExportBreadcrumbs.propTypes = {
  crumbs: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      onClick: PropTypes.func,
    }),
  ),
  onBack: PropTypes.func,
};
