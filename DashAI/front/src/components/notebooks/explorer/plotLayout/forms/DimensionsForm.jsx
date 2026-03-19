import React from "react";
import { TextField, Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function DimensionsForm({ data, handleTraceChange }) {
  const { t } = useTranslation(["datasets"]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {data[0].dimensions.map((dim, idx) => (
        <Box
          key={dim.label != null ? `dim-${dim.label}` : `dim-${idx}`}
          sx={{
            p: 2,
            border: "1px solid #444",
            borderRadius: 1,
            bgcolor: "#333",
          }}
        >
          <Typography
            variant="subtitle2"
            color="text.secondary"
            sx={{ mb: 2, color: "white" }}
          >
            {t("datasets:label.dimensionIdx", {
              idx: idx + 1,
              label: dim.label || `Dimension ${idx + 1}`,
            })}
          </Typography>

          {/* Dimension Title */}
          <TextField
            label={t("datasets:label.dimensionTitle")}
            variant="filled"
            value={dim.label || ""}
            onChange={(e) =>
              handleTraceChange(0, `dimensions.${idx}.label`, e.target.value)
            }
            fullWidth
            sx={{ mb: 2 }}
          />
        </Box>
      ))}
    </Box>
  );
}
