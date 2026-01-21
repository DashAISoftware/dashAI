import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";

export default function NoteBox({ message, className = "" }) {
  const theme = useTheme();
  const { t } = useTranslation(["common"]);
  return (
    <Box
      className={className}
      sx={{
        mt: 2,
        p: 2,
        bgcolor: theme.palette.background.box,
        borderRadius: 1,
        border: `1px solid ${theme.palette.ui.divider}`,
        mb: 2,
      }}
    >
      <Typography
        variant="subtitle2"
        sx={{ color: theme.palette.primary.main, mb: 1 }}
      >
        {t("common:note")}
      </Typography>
      <Typography variant="body2">{message}</Typography>
    </Box>
  );
}
