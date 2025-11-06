import { useEffect, useState } from "react";
import { Box } from "@mui/material";

export default function DocumentsBar({ selectedSessionId, taskName }) {
  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"auto"}
      bgcolor={"background.box"}
      borderRadius={2}
    ></Box>
  );
}
