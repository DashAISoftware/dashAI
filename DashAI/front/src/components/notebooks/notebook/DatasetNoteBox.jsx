import { Box, Typography } from "@mui/material";

export default function DatasetNoteBox() {
  return (
    <Box
      sx={{
        mt: 2,
        p: 2,
        bgcolor: "#212121",
        borderRadius: 1,
        border: "1px solid rgba(255, 255, 255, 0.1)",
        mb: 2,
      }}
    >
      <Typography variant="subtitle2" sx={{ color: "#00BEBB", mb: 1 }}>
        Note:
      </Typography>
      <Typography variant="body2">
        A copy of the selected dataset will be created to work in the notebook
        without altering the original.
      </Typography>
    </Box>
  );
}
