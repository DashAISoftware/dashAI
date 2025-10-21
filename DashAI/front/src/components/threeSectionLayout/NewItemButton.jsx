import AddIcon from "@mui/icons-material/Add";
import { Box, Button } from "@mui/material";

export default function NewItemButton({ onClick, title = "New Item" }) {
  return (
    <Box px={2} py={1}>
      <Button
        variant="contained"
        sx={{
          bgcolor: "primary.main",
          borderRadius: 1,
          mt: 1,
          px: 2,
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          height: "35px",
          width: "100%",
          textTransform: "none",
          "&:hover": { bgcolor: "primary.dark" },
        }}
        onClick={onClick}
        endIcon={<AddIcon />}
      >
        {title}
      </Button>
    </Box>
  );
}
