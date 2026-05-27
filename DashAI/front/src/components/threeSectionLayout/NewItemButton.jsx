import AddIcon from "@mui/icons-material/Add";
import { Box, Button } from "@mui/material";
import { t } from "i18next";

export default function NewItemButton({
  onClick,
  title = t("common:newItem", "New Item"),
}) {
  return (
    <Button
      variant="contained"
      sx={{
        bgcolor: "primary.main",
        borderRadius: 1,
        px: 4,
        py: 0,
        display: "flex",
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        height: "100%",
        width: "100%",
        textTransform: "none",
        "&:hover": { bgcolor: "primary.light" },
      }}
      onClick={onClick}
      endIcon={<AddIcon />}
    >
      {title}
    </Button>
  );
}
