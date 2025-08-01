import React from "react";
import PropTypes from "prop-types";

import { Box } from "@mui/material";

function ImageVisualizer({ data }) {
  return (
    <Box
      component="img"
      src={data}
      alt="Image"
      style={{ maxWidth: "100%", maxHeight: "100%" }}
    />
  );
}

ImageVisualizer.propTypes = {
  data: PropTypes.string.isRequired,
};

export default ImageVisualizer;
