import { Box } from "@mui/material";
import api from "../../api/api";

export function AudioMessage({ audio }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box
        component="audio"
        controls
        src={`${api.defaults.baseURL}/v1/generative-process/file/${audio}`}
        sx={{ maxWidth: "100%" }}
      />
    </Box>
  );
}
