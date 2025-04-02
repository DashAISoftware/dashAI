import React from "react";
import { Box, Typography } from "@mui/material";
import SessionMenu from "./SessionMenu";

export default function SessionBox({ name, id, onClick, onDelete, onInfo }) {
  return (
    <Box
      sx={{
        width: "100%",
        height: "40px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderRadius: 1,
        cursor: "pointer",
        p: 0.5,
        "&:hover": {
          backgroundColor: "#1E1E2F",
        },
      }}
      onClick={onClick}
    >
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        gap={0.5}
      >
        <Typography
          variant="h1"
          sx={{ fontSize: "12px", textOverflow: "ellipsis" }}
        >
          {name}
        </Typography>
      </Box>
      <Box onClick={(e) => e.stopPropagation()}>
        <SessionMenu sessionId={id} onInfo={onInfo} onDelete={onDelete} />
      </Box>
    </Box>
  );
}
