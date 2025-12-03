import AddIcon from "@mui/icons-material/Add";
import { Box, Button } from "@mui/material";

export default function NewItemButton({ onClick, title = "New Item" }) {
  return (
    <Button
      variant="contained"
      sx={{
        bgcolor: "primary.main",
        borderRadius: 1,
        px: 2,
        py: 0,
        display: "flex",
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        height: "100%",
        width: "100%",
        textTransform: "none",
        "&:hover": { bgcolor: "primary.dark" },
      }}
      onClick={onClick}
      endIcon={<AddIcon />}
    >
      {title}
    </Button>
  );
}
