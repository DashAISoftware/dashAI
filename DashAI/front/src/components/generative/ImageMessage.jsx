import { Box, useTheme } from "@mui/material";
import { useState } from "react";
import { FullscreenImageChat } from "./FullscreenImageChat";
import api from "../../api/api";
import { useTranslation } from "react-i18next";

export function ImageMessage({ image }) {
  const { t } = useTranslation(["common"]);
  const theme = useTheme();
  const [fullscreenImage, setFullscreenImage] = useState(null);

  const handleImageClick = () => {
    setFullscreenImage(image);
  };

  const handleCloseFullscreen = () => {
    setFullscreenImage(null);
  };

  return (
    <>
      <Box
        onClick={handleImageClick}
        sx={{
          cursor: "pointer",
          lineHeight: 0,
          "&:hover": { opacity: 0.9 },
          transition: theme.transitions.create("opacity"),
        }}
      >
        <img
          src={`${api.defaults.baseURL}/v1/generative-process/file/${image}`}
          alt={t("common:image")}
          style={{
            display: "block",
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
    </>
  );
}
