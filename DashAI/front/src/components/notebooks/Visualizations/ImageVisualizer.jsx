import PropTypes from "prop-types";

import { Box } from "@mui/material";

function ImageVisualizer({ data, minimalist = false }) {
  const imageStyles = minimalist
    ? {
        width: "100%",
        height: "100%",
        objectFit: "contain",
        objectPosition: "center",
      }
    : {
        maxWidth: "100%",
        maxHeight: "100%",
      };

  return <Box component="img" src={data} alt="Image" style={imageStyles} />;
}

ImageVisualizer.propTypes = {
  data: PropTypes.string.isRequired,
  minimalist: PropTypes.bool,
};

export default ImageVisualizer;
