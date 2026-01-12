import React from "react";
import { Box, Typography } from "@mui/material";
import SessionMenu from "./SessionMenu";
const { useTranslation } = require("react-i18next");

export default function SessionBox({
  isSelected,
  name,
  modelName,
  id,
  onClick,
  onDelete,
  onInfo,
}) {
  const { t } = useTranslation(["generative"]);

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
        bgcolor: isSelected ? "rgba(255, 255, 255, 0.05)" : "transparent",
        p: 0.5,
        "&:hover": {
          backgroundColor: isSelected
            ? "rgba(255, 255, 255, 0.05)"
            : "rgba(255, 255, 255, 0.05)",
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
            {name ? name : t("generative:label.untitledSession")}
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
