import React from "react";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import IconButton from "@mui/material/IconButton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useGenerative } from "../GenerativeContext";

/**
 * Breadcrumbs component for RAG navigation
 * @param {string} sessionName - Optional session name to show in breadcrumbs
 */
function RAGBreadcrumbs({ sessionName }) {
  const { t } = useTranslation(["generative"]);
  const navigate = useNavigate();
  const location = useLocation();
  const {
    setSelectedSessionId,
    setSelectedTaskName,
    setSelectedDisplayName,
    setStepIndex,
  } = useGenerative() ?? {};

  const navigateToGenerative = () => {
    setSelectedSessionId?.(null);
    setSelectedTaskName?.(null);
    setSelectedDisplayName?.(null);
    setStepIndex?.(0);
    navigate("/app/generative");
  };

  const getBreadcrumbs = () => {
    const path = location.pathname;
    if (!path.startsWith("/app/generative/RAG")) return [];

    const base = [
      { label: t("generative:rag.breadcrumbs.generative"), path: "/app/generative" },
      { label: t("generative:rag.breadcrumbs.rag"), path: "/app/generative/RAG" },
    ];

    if (path === "/app/generative/RAG/documents") return [...base, { label: t("generative:rag.breadcrumbs.documents"), path: null, current: true }];
    if (path === "/app/generative/RAG/prompts") return [...base, { label: t("generative:rag.breadcrumbs.prompts"), path: null, current: true }];

    if (sessionName) return [...base, { label: sessionName, path: null, current: true, isSession: true }];

    base[1] = { ...base[1], path: null, current: true };
    return base;
  };

  const breadcrumbs = getBreadcrumbs();

  const handleNavigate = (path) => {
    if (!path) return;
    if (path === "/app/generative") {
      navigateToGenerative();
      return;
    }
    if (path === "/app/generative/RAG") {
      setSelectedSessionId?.(null);
      setSelectedTaskName?.("RAGTask");
      setSelectedDisplayName?.(null);
      setStepIndex?.(0);
    }
    navigate(path);
  };

  const handleBack = () => {
    if (breadcrumbs.length > 1) {
      const parentBreadcrumb = breadcrumbs[breadcrumbs.length - 2];
      handleNavigate(parentBreadcrumb.path);
      return;
    }
    navigateToGenerative();
  };

  const showBackButton = breadcrumbs.length > 0;

  return (
    <Box 
      sx={{ 
        mb: 2,
        minHeight: '24px', // Ensure consistent height
        display: 'flex',
        alignItems: 'center',
        gap: 1
      }}
    >
      {showBackButton && (
        <IconButton
          onClick={handleBack}
          size="small"
          sx={{
            color: 'text.secondary',
            '&:hover': {
              color: 'primary.main',
              backgroundColor: 'action.hover'
            }
          }}
          aria-label={t("generative:rag.breadcrumbs.goBack")}
        >
          <ArrowBackIcon fontSize="small" />
        </IconButton>
      )}
      <Breadcrumbs 
        aria-label="breadcrumb" 
        sx={{ 
          minHeight: '24px', // Ensure consistent height
          display: 'flex',
          alignItems: 'center'
        }}
      >
        {breadcrumbs.map((breadcrumb, index) => {
          if (breadcrumb.current) {
            return (
              <Typography key={index} color="text.primary">
                {breadcrumb.isSession ? (
                  <>
                    <em>{breadcrumb.label}</em> {t("generative:rag.breadcrumbs.sessionSuffix")}
                  </>
                ) : (
                  breadcrumb.label
                )}
              </Typography>
            );
          } else {
            return (
              <Link
                key={index}
                underline="hover"
                color="inherit"
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  handleNavigate(breadcrumb.path);
                }}
                sx={{ cursor: "pointer" }}
              >
                {breadcrumb.label}
              </Link>
            );
          }
        })}
      </Breadcrumbs>
    </Box>
  );
}

export default RAGBreadcrumbs;