import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function DescriptionPanel() {
  const { t } = useTranslation(["common"]);

  return (
    <Box
      sx={{
        p: 2,
        bgcolor: "#2C2C2C",
        borderTop: "1px solid #444",
        minHeight: 80,
        maxHeight: 80,
        display: "flex",
        alignItems: "center",
        flexShrink: 0,
      }}
    >
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", fontStyle: "italic" }}
      >
        {t("common:hoverToolForDescription")}
      </Typography>
    </Box>
  );
}
