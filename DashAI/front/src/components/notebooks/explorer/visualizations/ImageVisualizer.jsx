import PropTypes from "prop-types";
import { Box, keyframes } from "@mui/material";
import { useEffect, useRef, useState } from "react";

function ImageVisualizer({ data, minimalist = false }) {
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const [scrollAnimation, setScrollAnimation] = useState(null);

  useEffect(() => {
    if (minimalist && containerRef.current && imageRef.current) {
      const updateAnimation = () => {
        const container = containerRef.current;
        const image = imageRef.current;

        if (container && image) {
          const containerHeight = container.clientHeight;
          const imageHeight = image.clientHeight;

          // Only create animation if image is taller than container
          if (imageHeight > containerHeight) {
            const translateDistance = imageHeight - containerHeight;

            const dynamicScrollY = keyframes`
              0% { transform: translateY(0px); }
              5% { transform: translateY(0px); }
              95% { transform: translateY(-${translateDistance}px); }
              100% { transform: translateY(-${translateDistance}px); }
            `;

            setScrollAnimation(dynamicScrollY);
          } else {
            setScrollAnimation(null);
          }
        }
      };

      // Small delay to ensure dimensions are available
      const timeoutId = setTimeout(updateAnimation, 100);

      // Update animation when image loads
      const image = imageRef.current;
      if (image.complete) {
        updateAnimation();
      } else {
        image.addEventListener("load", updateAnimation);
      }

      // Update animation on window resize
      window.addEventListener("resize", updateAnimation);

      return () => {
        clearTimeout(timeoutId);
        if (image) {
          image.removeEventListener("load", updateAnimation);
        }
        window.removeEventListener("resize", updateAnimation);
      };
    }
  }, [minimalist, data]);

  return (
    <Box
      ref={containerRef}
      sx={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: minimalist ? "flex-start" : "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      <Box
        ref={imageRef}
        component="img"
        src={data}
        alt="Image"
        sx={{
          maxWidth: "100%",
          height: "auto",
          objectFit: "contain",
          ...(minimalist &&
            scrollAnimation && {
              animation: `${scrollAnimation} 20s linear infinite`,
              pointerEvents: "none",
              userSelect: "none",
            }),
        }}
      />
    </Box>
  );
}

ImageVisualizer.propTypes = {
  data: PropTypes.string.isRequired,
  minimalist: PropTypes.bool,
};

export default ImageVisualizer;
