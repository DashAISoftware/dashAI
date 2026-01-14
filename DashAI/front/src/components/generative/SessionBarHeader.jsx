import React from "react";
import { Box, Typography } from "@mui/material";

export default function SessionBarHeader() {
  return (
    <Box
      display="flex"
      alignItems="center"
      justifyContent="space-between"
      height={"70px"}
      px={2}
      py={1.5}
    >
      <Typography
        variant="h6"
        sx={{
          fontWeight: "bold",
          "& span": { color: theme.palette.accent.main },
        }}
      >
        <span>D</span>a<span>sh</span>
      </Typography>
    </Box>
  );
}
