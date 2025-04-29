import { Box, useTheme } from "@mui/material";
import { useState } from "react";
import { FullscreenImageChat } from "./FullscreenImageChat";

export function ImageMessage({ images }) {
  const theme = useTheme();
  const [fullscreenImage, setFullscreenImage] = useState(null);

  const handleImageClick = (imageData) => {
    setFullscreenImage(imageData);
  };

  const handleCloseFullscreen = () => {
    setFullscreenImage(null);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {images?.map((image, index) => (
        <Box
          key={index}
          onClick={() => handleImageClick(image)}
          sx={{
            cursor: "pointer",
            "&:hover": {
              opacity: 0.9,
            },
            transition: theme.transitions.create("opacity"),
          }}
        >
          <img
            src={`data:image/png;base64,${image}`}
            alt={`Image ${index + 1}`}
            style={{
              maxWidth: "100%",
              maxHeight: "300px",
              objectFit: "contain",
              borderRadius: theme.shape.borderRadius,
            }}
          />
        </Box>
      ))}
      <FullscreenImageChat
        open={fullscreenImage !== null}
        onClose={handleCloseFullscreen}
        imageData={fullscreenImage}
      />
    </Box>
  );
}
