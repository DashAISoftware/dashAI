import React from "react";
import { Box } from "@mui/material";

export default function MainGenerativeBox({ children }) {
  return (
    <Box
      width={"100%"}
      height={"100%"}
      borderRadius={2}
      bgcolor={"#121212"}
      p={2}
    >
      {children}
    </Box>
  );
}
