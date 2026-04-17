import React from "react";
import { Alert, AlertTitle, Box } from "@mui/material";
import { useTranslation } from "react-i18next";

function ValidationStatus({ result }) {
  const { t } = useTranslation("customComponents");
  if (!result) return null;

  if (result.ok) {
    return (
      <Alert severity="success" sx={{ mb: 1 }}>
        <AlertTitle>{t("validation.okTitle")}</AlertTitle>
        {t("validation.okBody")}
        {result.warnings?.length > 0 && (
          <Box mt={1} component="ul" sx={{ pl: 3 }}>
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </Box>
        )}
      </Alert>
    );
  }

  return (
    <Alert severity="error" sx={{ mb: 1 }}>
      <AlertTitle>{t("validation.errorTitle")}</AlertTitle>
      <Box component="ul" sx={{ pl: 3, m: 0 }}>
        {result.errors.map((e, i) => (
          <li key={i}>
            <code style={{ whiteSpace: "pre-wrap" }}>{e}</code>
          </li>
        ))}
      </Box>
    </Alert>
  );
}

export default ValidationStatus;
