import React from "react";
import { Box } from "@mui/material";

export default function MainGenerativeBox({ children }) {
  return (
    <Box width={"1063px"} height={"auto"}>
      <Box
        bgcolor={"#212121"}
        width={"100%"}
        height={"100%"}
        borderRadius={2}
      ></Box>
      {children}
    </Box>
  );
}
