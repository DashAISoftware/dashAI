import { Box, useTheme } from "@mui/material";
import { useState } from "react";
import { FullscreenImageChat } from "./FullscreenImageChat";
import api from "../../api/api";

export function ImageMessage({ image }) {
  const theme = useTheme();
  const [fullscreenImage, setFullscreenImage] = useState(null);

  const handleImageClick = () => {
    setFullscreenImage(image);
  };

  const handleCloseFullscreen = () => {
    setFullscreenImage(null);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Box
        onClick={handleImageClick}
        sx={{
          cursor: "pointer",
          "&:hover": {
            opacity: 0.9,
          },
          transition: theme.transitions.create("opacity"),
        }}
      >
        <img
          src={`${api.defaults.baseURL}/v1/generative-process/image/${image}`}
          alt="Image"
          style={{
            maxWidth: "100%",
            maxHeight: "300px",
            objectFit: "contain",
            borderRadius: theme.shape.borderRadius,
          }}
        />
      </Box>
      <FullscreenImageChat
        open={fullscreenImage !== null}
        onClose={handleCloseFullscreen}
        imageData={fullscreenImage}
      />
    </Box>
  );
}
