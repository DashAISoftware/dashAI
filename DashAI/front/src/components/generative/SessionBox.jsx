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
        bgcolor: isSelected ? "action.selected" : "transparent",
        p: 1,
        "&:hover": {
          backgroundColor: isSelected ? "action.selected" : "action.hover",
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
            variant="body1"
            color="text.primary"
            noWrap
            sx={{ maxWidth: 180 }}
          >
            {name ? name : t("generative:label.untitledSession")}
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            noWrap
            sx={{ maxWidth: 150, pl: 2 }}
          >
            {modelName}
          </Typography>
        </Box>
      </Box>
      <SessionMenu sessionId={id} onInfo={onInfo} onDelete={onDelete} />
    </Box>
  );
}
