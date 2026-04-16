import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { FormControl, Select, MenuItem, Box } from "@mui/material";
import LanguageIcon from "@mui/icons-material/Language";

export default function LanguageSelector() {
  const { i18n } = useTranslation();
  const [language, setLanguage] = useState(i18n.language);

  const handleLanguageChange = (event) => {
    const newLanguage = event.target.value;
    i18n.changeLanguage(newLanguage);
    setLanguage(newLanguage);
  };

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <LanguageIcon sx={{ color: "text.secondary" }} />
      <FormControl size="small" sx={{ minWidth: 120 }}>
        <Select
          value={language}
          onChange={handleLanguageChange}
          displayEmpty
          sx={{
            "& .MuiSelect-select": {
              display: "flex",
              alignItems: "center",
              gap: 1,
            },
          }}
        >
          <MenuItem value="es">
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <span>🇨🇱</span>
              <span>Español</span>
            </Box>
          </MenuItem>
          <MenuItem value="en">
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <span>🇺🇸</span>
              <span>English</span>
            </Box>
          </MenuItem>
        </Select>
      </FormControl>
    </Box>
  );
}
