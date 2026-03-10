import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useState, useEffect } from "react";

export function WaitingAnimationChat({ isActive }) {
  const theme = useTheme();
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
      <Typography variant="body2" sx={{ color: theme.palette.text.primary }}>
        {dots}
      </Typography>
    </Box>
  );
}
