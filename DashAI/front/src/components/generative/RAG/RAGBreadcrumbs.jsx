import React from "react";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import IconButton from "@mui/material/IconButton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import { useNavigate, useLocation } from "react-router-dom";

/**
 * Breadcrumbs component for RAG navigation
 * @param {boolean} isEmbedded - Whether this is embedded in the main Generative flow or standalone
 * @param {function} onNavigateToGenerative - Callback function to handle navigation to Generative (for embedded mode)
 * @param {string} sessionName - Optional session name to show in breadcrumbs
 */
function RAGBreadcrumbs({ isEmbedded = false, onNavigateToGenerative, sessionName }) {
  const navigate = useNavigate();
  const location = useLocation();

  const getBreadcrumbs = () => {
    const path = location.pathname;
    
    if (path === "/app/generative/rag" || isEmbedded) {
      const breadcrumbs = [
        { label: "Generative", path: "/app/generative" },
        { label: "RAG", path: "/app/generative/rag" }
      ];
      
      // If session name is provided, add it as the current breadcrumb
      if (sessionName) {
        breadcrumbs.push({ label: sessionName, path: null, current: true, isSession: true });
      } else {
        // Mark RAG as current if no session name
        breadcrumbs[breadcrumbs.length - 1].current = true;
        breadcrumbs[breadcrumbs.length - 1].path = null;
      }
      
      return breadcrumbs;
    } else if (path === "/app/generative/rag/sessions") {
      return [
        { label: "Generative", path: "/app/generative" },
        { label: "RAG", path: "/app/generative/rag" },
        { label: "Sessions", path: null, current: true }
      ];
    } else if (path === "/app/generative/rag/documents") {
      return [
        { label: "Generative", path: "/app/generative" },
        { label: "RAG", path: "/app/generative/rag" },
        { label: "Documents", path: null, current: true }
      ];
    } else if (path === "/app/generative/rag/prompts") {
      return [
        { label: "Generative", path: "/app/generative" },
        { label: "RAG", path: "/app/generative/rag" },
        { label: "Prompts", path: null, current: true }
      ];
    }
    
    return [];
  };

  const breadcrumbs = getBreadcrumbs();

  const handleNavigate = (path) => {
    if (path) {
      // If we're in embedded mode and trying to navigate to generative, use the callback
      if (isEmbedded && path === "/app/generative" && onNavigateToGenerative) {
        onNavigateToGenerative();
      } else {
        navigate(path);
      }
    }
  };

  const handleBack = () => {
    // Find the parent breadcrumb (second to last)
    if (breadcrumbs.length > 1) {
      const parentBreadcrumb = breadcrumbs[breadcrumbs.length - 2];
      handleNavigate(parentBreadcrumb.path);
    } else if (breadcrumbs.length === 1 && !isEmbedded) {
      // If we're at the top level (RAG) and not embedded, go to generative
      navigate("/app/generative");
    } else if (isEmbedded && onNavigateToGenerative) {
      // If embedded, use the callback
      onNavigateToGenerative();
    }
  };

  // Don't show back button if we're at the root level and embedded
  const showBackButton = !isEmbedded || breadcrumbs.length > 1;

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
          aria-label="Go back"
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
                    <em>{breadcrumb.label}</em> session
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