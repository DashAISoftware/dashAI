import AddIcon from "@mui/icons-material/Add";
import { Box, Button } from "@mui/material";
import React from "react";
import Typography from "@mui/material/Typography";

export default function NewSessionButton({ onClick }) {
  return (
    <Box px={2} py={1}>
      <Button
        sx={{
          bgcolor: "#374151",
          color: "white",
          borderRadius: 1,
          mt: 1,
          py: 1,
          px: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          cursor: "pointer",
          "&:hover": {
            bgcolor: "#475569",
          },
          height: "45px",
          width: "100%",
          textTransform: "none",
        }}
        onClick={onClick}
      >
        <AddIcon sx={{ mr: 1 }} />
        <Typography>New session</Typography>
      </Button>
    </Box>
  );
}
