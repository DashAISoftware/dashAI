import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";

export default function NoteBox({ message, className = "", ...props }) {
  const theme = useTheme();
  const { t } = useTranslation(["common"]);
  return (
    <Box
      className={className}
      {...props}
      sx={{
        p: 4,
        bgcolor: theme.palette.background.box,
        borderRadius: 1,
        border: `1px solid ${theme.palette.ui.divider}`,
      }}
    >
      <Typography
        variant="subtitle2"
        sx={{ color: theme.palette.primary.main, mb: 2 }}
      >
        {t("common:note")}
      </Typography>
      <Typography variant="body2">{message}</Typography>
    </Box>
  );
}
