import { Box, Typography } from "@mui/material";
import { useState, useEffect } from "react";

export function WaitingAnimationChat({ isActive }) {
  const [dots, setDots] = useState("");

  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      setDots((prev) => {
        if (prev === "") return ".";
        if (prev === ".") return "..";
        if (prev === "..") return "...";
        return "";
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isActive]);

  return (
    <Box sx={{ minWidth: "40px", minHeight: "24px" }}>
      <Typography variant="body2" color="text.primary">
        {dots}
      </Typography>
    </Box>
  );
}
