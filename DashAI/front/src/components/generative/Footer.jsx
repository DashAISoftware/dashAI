import React from "react";
import { Box, Avatar, Divider } from "@mui/material";

export default function Footer() {
  return (
    <Box
      display={"flex"}
      justifyContent={"center"}
      alignItems={"center"}
      flexDirection={"column"}
      py={2}
    >
      <Divider sx={{ width: "100%", bgcolor: "divider" }} />
      <Avatar
        alt="DashAI Logo"
        src="/images/logo.png"
        variant="square"
        sx={{ width: 120, p: 0, mt: 2 }}
      />
    </Box>
  );
}
