import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";

export default function DescriptionPanel() {
  const theme = useTheme();
  const { t } = useTranslation(["common"]);
  return (
    <Box
      sx={{
        p: 2,
        bgcolor: theme.palette.ui.panelDark,
        borderTop: `1px solid ${theme.palette.ui.borderLight}`,
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
