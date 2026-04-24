import { Box, useTheme } from "@mui/material";
import api from "../../api/api";

export function VideoMessage({ video }) {
  const theme = useTheme();
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Box
        component="video"
        controls
        src={`${api.defaults.baseURL}/v1/generative-process/file/${video}`}
        sx={{
          maxWidth: "100%",
          maxHeight: "300px",
          borderRadius: theme.shape.borderRadius,
        }}
      />
    </Box>
  );
}
