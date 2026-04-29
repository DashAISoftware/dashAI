import Breadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import IconButton from "@mui/material/IconButton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useGenerative } from "./GenerativeContext";

export default function GenerativeBreadcrumbs() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const { t } = useTranslation(["generative", "common"]);
  const { tasks, sessions } = useGenerative();

  const rootCrumb = { label: t("common:generative"), path: "/app/generative" };

  const getBreadcrumbs = () => {
    const path = location.pathname;

    if (path.startsWith("/app/generative/sessions/new/") && params.taskName) {
      const task = tasks.find((tk) => tk.name === params.taskName);
      const taskLabel = task?.display_name ?? params.taskName;
      return [rootCrumb, { label: taskLabel, path: null, current: true }];
    }

    if (path.startsWith("/app/generative/sessions/") && params.id) {
      const session = sessions.find((s) => s.id === Number(params.id));
      const name = session?.name ?? `#${params.id}`;
      return [rootCrumb, { label: name, path: null, current: true }];
    }

    return [{ ...rootCrumb, path: null, current: true }];
  };

  const breadcrumbs = getBreadcrumbs();

  const handleNavigate = (path) => {
    if (!path) return;
    navigate(path);
  };

  const handleBack = () => {
    if (breadcrumbs.length > 1) {
      const parent = breadcrumbs[breadcrumbs.length - 2];
      handleNavigate(parent.path);
      return;
    }
    navigate("/app/generative");
  };

  const showBackButton = breadcrumbs.length > 1;

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
      {showBackButton && (
        <IconButton
          onClick={handleBack}
          size="small"
          sx={{
            color: "text.secondary",
            "&:hover": {
              color: "primary.main",
              backgroundColor: "action.hover",
            },
          }}
          aria-label="Go back"
        >
          <ArrowBackIcon fontSize="small" />
        </IconButton>
      )}
      <Breadcrumbs
        aria-label="breadcrumb"
        sx={{
          minHeight: "24px",
          display: "flex",
          alignItems: "center",
        }}
      >
        {breadcrumbs.map((crumb, index) => {
          if (crumb.current) {
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
                handleNavigate(crumb.path);
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
