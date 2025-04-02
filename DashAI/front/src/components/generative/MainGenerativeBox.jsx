import React from "react";
import { Box } from "@mui/material";

export default function MainGenerativeBox({ children }) {
  return (
    <Box
      width={"1063px"}
      height={"auto"}
      borderRadius={2}
      bgcolor={"#212121"}
      p={2}
    >
      {children}
    </Box>
  );
}
