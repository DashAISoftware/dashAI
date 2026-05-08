import Breadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import IconButton from "@mui/material/IconButton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

/**
 * Breadcrumbs for the Hub module dataset-list view.
 *
 * @param {string} sourceDisplayName - Human-readable source name shown as the current crumb.
 */
export default function HubBreadcrumbs({ sourceDisplayName }) {
  const navigate = useNavigate();
  const { t } = useTranslation(["hub"]);

  const handleBack = () => navigate("/app/hub");

  return (
    <Box sx={{ mb: 2, minHeight: "24px", display: "flex", alignItems: "center", gap: 1 }}>
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
      <Breadcrumbs aria-label="breadcrumb" sx={{ minHeight: "24px", display: "flex", alignItems: "center" }}>
        <Link
          underline="hover"
          color="inherit"
          href="#"
          onClick={(e) => { e.preventDefault(); handleBack(); }}
          sx={{ cursor: "pointer" }}
        >
          {t("hub:title")}
        </Link>
        <Typography color="text.primary">{sourceDisplayName}</Typography>
      </Breadcrumbs>
    </Box>
  );
}
