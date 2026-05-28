import { Box } from "@mui/material";

export function InlineCode({ children, ...props }) {
  return (
    <Box
      component="code"
      sx={{
        px: 1,
        py: 1,
        borderRadius: 0.5,
        bgcolor: "action.hover",
        fontSize: "0.85em",
      }}
      {...props}
    >
      {children}
    </Box>
  );
}
