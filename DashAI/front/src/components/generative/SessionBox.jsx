import React from "react";
import { Box, Typography, Button, IconButton } from "@mui/material";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";

export default function SessionBox({ name }) {
  return (
    <Button
      sx={{
        width: "100%",
        height: "40px",
        display: "flex",
        justifyContent: "space-between",
        textTransform: "none",
      }}
      borderRadius={1}
      p={0.5}
    >
      <Box
        display={"flex"}
        flexDirection={"column"}
        alignItems={"center"}
        justifyContent={"center"}
        gap={0.5}
      >
        <Typography
          variant="h1"
          sx={{ fontSize: "12px", textOverflow: "ellipsis" }}
        >
          {name}
        </Typography>
      </Box>
      <IconButton>
        <MoreHorizIcon />
      </IconButton>
    </Button>
  );
}
