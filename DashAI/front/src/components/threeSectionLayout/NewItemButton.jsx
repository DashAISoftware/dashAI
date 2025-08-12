import AddIcon from "@mui/icons-material/Add";
import { Box, Button } from "@mui/material";
import Typography from "@mui/material/Typography";

export default function NewItemButton({ onClick, title = "New Item" }) {
  return (
    <Box px={2} py={1}>
      <Button
        sx={{
          bgcolor: "primary.main",
          color: "white",
          borderRadius: 1,
          mt: 1,
          px: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          cursor: "pointer",
          "&:hover": {
            bgcolor: "primary.dark",
          },
          height: "40px",
          width: "100%",
          textTransform: "none",
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
        }}
        onClick={onClick}
      >
        <Typography>{title}</Typography>
        <AddIcon />
      </Button>
    </Box>
  );
}
