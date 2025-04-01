import { Box } from "@mui/material";
import React from "react";
import AddCardIcon from "@mui/icons-material/AddCard";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";

export default function NewSession() {
  return (
    <Box
      display={"flex"}
      justifyContent={"space-between"}
      alignItems={"center"}
      onClick={() => console.log("New session clicked")}
      sx={{
        cursor: "pointer",
        backgroundColor: "#161925",
        width: "100%",
        height: "40px",
        p: 0.5,
        "&:hover": {
          backgroundColor: "#1E1E2F",
        },
      }}
    >
      <Typography
        display={"flex"}
        flexDirection={"column"}
        justifyContent={"center"}
        sx={{ opacity: "0.5" }}
      >
        Create a new session
      </Typography>
      <Box display={"flex"} justifyContent={"center"} alignItems={"center"}>
        <AddCardIcon />
      </Box>
    </Box>
  );
}
