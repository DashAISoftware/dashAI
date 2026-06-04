import React from "react";
import ReactDOM from "react-dom/client";
import "./styles/geist-font.css";
import "./index.css";
import CssBaseline from "@mui/material/CssBaseline";
import App from "./App";
import reportWebVitals from "./reportWebVitals";
import { SnackbarProvider } from "notistack";
import { CustomThemeProvider } from "./contexts/ThemeContext";

// Benign browser warning fired by ResizeObserver when observers cascade in the
// same frame (Monaco + resizable panels). The CRA dev overlay treats any window
// error as fatal; suppress these specific strings so the overlay stays quiet.
const RESIZE_OBSERVER_ERRORS = [
  "ResizeObserver loop completed with undelivered notifications.",
  "ResizeObserver loop limit exceeded",
];
window.addEventListener("error", (event) => {
  if (RESIZE_OBSERVER_ERRORS.some((msg) => event.message?.includes(msg))) {
    event.stopImmediatePropagation();
    event.preventDefault();
  }
});
window.addEventListener("unhandledrejection", (event) => {
  const msg = event.reason?.message || String(event.reason || "");
  if (RESIZE_OBSERVER_ERRORS.some((m) => msg.includes(m))) {
    event.stopImmediatePropagation();
    event.preventDefault();
  }
});

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
