import Breadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import IconButton from "@mui/material/IconButton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

/**
 * Breadcrumbs for the Hub module.
 *
 * @param {string} [sourceDisplayName] - Simple mode: human-readable source name (current crumb).
 * @param {Array<{label: string, onClick?: function}>} [crumbs] - Full mode: explicit crumb list.
 *   Last entry without onClick renders as plain text (current page); others render as links.
 * @param {function} [onBack] - Custom back-button handler. Defaults to navigating to /app/data/hub.
 */
export default function HubBreadcrumbs({ sourceDisplayName, crumbs, onBack }) {
  const navigate = useNavigate();
  const { t } = useTranslation(["hub", "common"]);

  const rootCrumbs = [
    { label: t("common:datasets"), onClick: () => navigate("/app/data") },
    { label: t("hub:title"), onClick: () => navigate("/app/data/hub") },
  ];

  const resolvedCrumbs = crumbs
    ? [...rootCrumbs, ...crumbs.slice(1)]
    : [...rootCrumbs, { label: sourceDisplayName }];

  const handleBack = onBack ?? (() => navigate("/app/data/hub"));

  return (
    <Box
      sx={{
        mb: 2,
        minHeight: "24px",
        display: "flex",
        alignItems: "center",
        gap: 1,
      }}
    >
      <IconButton
        onClick={handleBack}
        size="small"
        sx={{
          color: "text.secondary",
          "&:hover": { color: "primary.main", backgroundColor: "action.hover" },
        }}
        aria-label="Go back"
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
              href="#"
              onClick={(e) => {
                e.preventDefault();
                crumb.onClick();
              }}
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
