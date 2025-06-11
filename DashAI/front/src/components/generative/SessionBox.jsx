import React from "react";
import { Box, Typography } from "@mui/material";
import SessionMenu from "./SessionMenu";

export default function SessionBox({
  isSelected,
  name,
  modelName,
  id,
  onClick,
  onDelete,
  onInfo,
}) {
  return (
    <Box
      sx={{
        width: "100%",
        height: "50px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderRadius: 1,
        cursor: isSelected ? "default" : "pointer",
        bgcolor: isSelected ? "#1E1E2F" : "transparent",
        p: 0.5,
        "&:hover": {
          backgroundColor: isSelected ? "#1E1E2F" : "#1E1E2F",
        },
      }}
      onClick={isSelected ? undefined : onClick}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          width: "100%",
        }}
      >
        <Box>
          <Typography
            variant="body2"
            noWrap
            sx={{ maxWidth: 180, fontSize: 14 }}
          >
            {name ? name : "Untitled Session"}
          </Typography>
          <Typography
            variant="caption"
            noWrap
            sx={{ maxWidth: 150, fontSize: 10, pl: 1 }}
          >
            {modelName}
          </Typography>
        </Box>
      </Box>
      <SessionMenu sessionId={id} onInfo={onInfo} onDelete={onDelete} />
    </Box>
  );
}
