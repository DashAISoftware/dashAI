import Breadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import IconButton from "@mui/material/IconButton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import PropTypes from "prop-types";

const UPLOAD_BASE_PATH = "/app/data/datasets/new";
const UPLOAD_CONFIGURE_PATH = `${UPLOAD_BASE_PATH}/configure`;

export default function DatasetBreadcrumbs({ selectedDataloader }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation(["datasets", "common"]);

  const step = location.pathname.startsWith(UPLOAD_CONFIGURE_PATH) ? 1 : 0;

  const rootCrumb = {
    label: t("common:datasets"),
    path: "/app/data/datasets",
  };

  const selectCrumb = {
    label: t("datasets:label.selectDataloader"),
    path: step === 1 ? UPLOAD_BASE_PATH : null,
    current: step === 0,
  };

  const crumbs = [rootCrumb, selectCrumb];

  if (step === 1 && selectedDataloader?.name) {
    crumbs.push({
      label: selectedDataloader.display_name || selectedDataloader.name,
      path: null,
      current: true,
    });
  }

  const handleNavigate = (path) => {
    if (!path) return;
    navigate(path);
  };

  const handleBack = () => {
    const parent = crumbs[crumbs.length - 2];
    handleNavigate(parent?.path ?? "/app/data/datasets");
  };

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
        {crumbs.map((crumb, index) =>
          crumb.current ? (
            <Typography key={index} color="text.primary">
              {crumb.label}
            </Typography>
          ) : (
            <Link
              key={index}
              underline="hover"
              color="inherit"
              href="#"
              onClick={(e) => {
                e.preventDefault();
                handleNavigate(crumb.path);
              }}
              sx={{ cursor: "pointer" }}
            >
              {crumb.label}
            </Link>
          ),
        )}
      </Breadcrumbs>
    </Box>
  );
}

DatasetBreadcrumbs.propTypes = {
  selectedDataloader: PropTypes.shape({
    name: PropTypes.string,
    display_name: PropTypes.string,
  }),
};
