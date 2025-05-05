import { Box, Typography } from "@mui/material";

export function TextMessage({ message }) {
  return (
    <Box>
      <Typography variant="body2" color="text.primary">
        {message}
      </Typography>
    </Box>
  );
}
