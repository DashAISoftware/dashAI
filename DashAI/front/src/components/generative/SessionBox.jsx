import React from "react";
import { Box, Typography } from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import SessionMenu from "./SessionMenu";

export default function SessionBox({ name, id, onClick, onDelete, onInfo }) {
  return (
    <Box
      sx={{
        width: "100%",
        height: "50px",
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
        alignItems="center"
        justifyContent={"flex-start"}
        width="100%"
      >
        <AutoAwesomeIcon sx={{ color: "#16FFFF", mr: 1, fontSize: 18 }} />
        <Box>
          <Typography variant="body2" noWrap sx={{ maxWidth: 150 }}>
            {name}
          </Typography>
        </Box>
      </Box>
      <SessionMenu sessionId={id} onInfo={onInfo} onDelete={onDelete} />
    </Box>
  );
}
