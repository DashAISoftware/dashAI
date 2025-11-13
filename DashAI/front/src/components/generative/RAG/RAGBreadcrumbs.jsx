import React from "react";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import { useNavigate, useLocation } from "react-router-dom";

/**
 * Breadcrumbs component for RAG navigation
 * @param {boolean} isEmbedded - Whether this is embedded in the main Generative flow or standalone
 * @param {function} onNavigateToGenerative - Callback function to handle navigation to Generative (for embedded mode)
 */
function RAGBreadcrumbs({ isEmbedded = false, onNavigateToGenerative }) {
  const navigate = useNavigate();
  const location = useLocation();

  const getBreadcrumbs = () => {
    const path = location.pathname;
    
    if (path === "/app/generative/rag" || isEmbedded) {
      return [
        { label: "Generative", path: "/app/generative" },
        { label: "RAG", path: null, current: true }
      ];
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

  return (
    <Breadcrumbs 
      aria-label="breadcrumb" 
      sx={{ 
        mb: 2,
        minHeight: '24px', // Ensure consistent height
        display: 'flex',
        alignItems: 'center'
      }}
    >
      {breadcrumbs.map((breadcrumb, index) => {
        if (breadcrumb.current) {
          return (
            <Typography key={index} color="text.primary">
              {breadcrumb.label}
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
  );
}

export default RAGBreadcrumbs;