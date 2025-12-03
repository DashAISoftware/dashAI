import React from "react";
import { TextField, Box, Typography } from "@mui/material";

export default function DimensionsForm({ data, handleTraceChange }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {data[0].dimensions.map((dim, idx) => (
        <Box
          key={idx}
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
            Dimension {idx + 1}: {dim.label || `Dimension ${idx + 1}`}
          </Typography>

          {/* Dimension Title */}
          <TextField
            label="Dimension Title"
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
