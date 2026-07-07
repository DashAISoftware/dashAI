import React from "react";
import { useLocation } from "react-router-dom";
import { createTheme, ThemeProvider, useTheme } from "@mui/material/styles";

const MODULE_PRIMARIES = {
  "/app/data": {
    dark: { main: "#FFA578", contrastText: "#191817", hover: "#79310C" },
    light: { main: "#79310C", contrastText: "#FEFEFF", hover: "#FFA578" },
  },
  "/app/models": {
    dark: { main: "#A7C7FF", contrastText: "#191817", hover: "#2C7AFF" },
    light: { main: "#2C7AFF", contrastText: "#FEFEFF", hover: "#A7C7FF" },
  },
  "/app/generative": {
    dark: { main: "#90F1C4", contrastText: "#191817", hover: "#005967" },
    light: { main: "#005967", contrastText: "#FEFEFF", hover: "#90F1C4" },
  },
  "/app/plugins": {
    dark: { main: "#FEE8FF", contrastText: "#191817", hover: "#A54DA9" },
    light: { main: "#A54DA9", contrastText: "#FEFEFF", hover: "#FEE8FF" },
  },
};

function getModuleKey(pathname) {
  if (pathname.startsWith("/app/data")) return "/app/data";
  if (pathname.startsWith("/app/models")) return "/app/models";
  if (pathname.startsWith("/app/generative")) return "/app/generative";
  if (pathname.startsWith("/app/plugins")) return "/app/plugins";
  return null;
}

export default function ModuleThemeWrapper({ children }) {
  const location = useLocation();
  const baseTheme = useTheme();

  const moduleKey = getModuleKey(location.pathname);
  const colors = moduleKey ? MODULE_PRIMARIES[moduleKey] : null;

  if (!colors) return children;

  const { main, contrastText, hover } = colors[baseTheme.palette.mode];

  const moduleTheme = createTheme(baseTheme, {
    palette: {
      primary: { main, light: hover, contrastText },
      action: {
        hover: `${hover}0F`,
        selected: `${hover}1A`,
      },
    },
  });

  return <ThemeProvider theme={moduleTheme}>{children}</ThemeProvider>;
}
