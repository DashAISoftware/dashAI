import { Box, Typography } from "@mui/material";

export default function DescriptionPanel() {
  return (
    <Box
      sx={{
        p: 2,
        bgcolor: "#2C2C2C",
        borderTop: "1px solid #444",
        minHeight: 80,
        maxHeight: 80,
        display: "flex",
        alignItems: "center",
        flexShrink: 0,
      }}
    >
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", fontStyle: "italic" }}
      >
        Hover over a tool to see its description
      </Typography>
    </Box>
  );
}
