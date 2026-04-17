import React from "react";
import {
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Tooltip,
  Box,
} from "@mui/material";
import { useTranslation } from "react-i18next";

function BaseClassSelector({ value, onChange, options, disabled = false }) {
  const { t } = useTranslation("customComponents");
  return (
    <FormControl fullWidth size="small" disabled={disabled}>
      <InputLabel>{t("fields.baseClass")}</InputLabel>
      <Select
        value={value || ""}
        label={t("fields.baseClass")}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => {
          const item = (
            <MenuItem key={opt.name} value={opt.name} disabled={!opt.enabled}>
              <Box display="flex" flexDirection="column">
                <span>{opt.name}</span>
                <span style={{ fontSize: "0.75em", opacity: 0.65 }}>
                  {opt.type}
                  {!opt.enabled ? ` — ${t("comingSoon")}` : ""}
                </span>
              </Box>
            </MenuItem>
          );
          if (!opt.enabled) {
            return (
              <Tooltip key={opt.name} title={t("comingSoon")} placement="right">
                <span>{item}</span>
              </Tooltip>
            );
          }
          return item;
        })}
      </Select>
    </FormControl>
  );
}

export default BaseClassSelector;
