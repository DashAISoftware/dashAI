import { Box, Typography } from "@mui/material";

export default function DatasetView({ dataset }) {
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      height="100%"
      p={2}
    >
      <Typography variant="h5" gutterBottom>
        Dataset View
      </Typography>
      <Typography variant="body1">
        Dataset ID: <strong>{dataset.id}</strong>
      </Typography>
    </Box>
  );
}
