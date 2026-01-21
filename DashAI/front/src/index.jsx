import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import CssBaseline from "@mui/material/CssBaseline";
import App from "./App";
import reportWebVitals from "./reportWebVitals";
import { SnackbarProvider } from "notistack";
import { CustomThemeProvider } from "./contexts/ThemeContext";

const root = ReactDOM.createRoot(document.getElementById("root"));
import "./utils/i18n";

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

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
