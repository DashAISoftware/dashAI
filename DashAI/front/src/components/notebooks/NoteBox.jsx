import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function NoteBox({ message, className = "" }) {
  const { t } = useTranslation(["common"]);
  return (
    <Box
      className={className}
      sx={{
        mt: 2,
        p: 2,
        bgcolor: "#212121",
        borderRadius: 1,
        border: "1px solid rgba(255, 255, 255, 0.1)",
        mb: 2,
      }}
    >
      <Typography variant="subtitle2" sx={{ color: "#00BEBB", mb: 1 }}>
        {t("common:note")}
      </Typography>
      <Typography variant="body2">{message}</Typography>
    </Box>
  );
}
