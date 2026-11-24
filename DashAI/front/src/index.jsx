import React from "react";
import ReactDOM from "react-dom/client";
import "./styles/geist-font.css";
import "./index.css";
import CssBaseline from "@mui/material/CssBaseline";
import App from "./App";
import { SnackbarProvider } from "notistack";
import { CustomThemeProvider } from "./contexts/ThemeContext";
import "./utils/i18n";

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <CustomThemeProvider>
      <SnackbarProvider
        anchorOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        variant="error"
      >
        <CssBaseline />
        <App />
      </SnackbarProvider>
    </CustomThemeProvider>
  </React.StrictMode>,
);
