import { Box } from "@mui/material";
import React from "react";
import AddCardIcon from "@mui/icons-material/AddCard";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";

export default function NewSession() {
  return (
    <Box display={"flex"} justifyContent={"space-between"}>
      <Typography
        display={"flex"}
        flexDirection={"column"}
        justifyContent={"center"}
        sx={{ opacity: "0.5" }}
      >
        Create a new session
      </Typography>
      <Box>
        <IconButton type="button" sx={{ p: "10px" }}>
          <AddCardIcon />
        </IconButton>
      </Box>
    </Box>
  );
}
