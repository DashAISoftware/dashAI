import React from "react";
import PropTypes from "prop-types";
import { Box, Button } from "@mui/material";
import ArrowBackIosIcon from "@mui/icons-material/ArrowBackIos";

function PipelineHeader({ activeTab, setActiveTab, navigate }) {
  return (
    <Box
      sx={{
        position: "relative",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        mb: 4,
      }}
    >
      <Button
        onClick={() => navigate("/app/pipelines")}
        sx={{ position: "absolute", left: 0, fontSize: "1rem" }}
      >
        <ArrowBackIosIcon />
      </Button>

      <Box>
        <Button
          onClick={() => setActiveTab("flow")}
          variant={activeTab === "flow" ? "contained" : "text"}
          sx={{ mr: 2, fontSize: "1.1rem" }}
        >
          Design
        </Button>
        <Button
          onClick={() => setActiveTab("results")}
          variant={activeTab === "results" ? "contained" : "text"}
          sx={{ fontSize: "1.1rem" }}
        >
          Results
        </Button>
      </Box>
    </Box>
  );
}

PipelineHeader.propTypes = {
  activeTab: PropTypes.oneOf(["flow", "results"]).isRequired,
  setActiveTab: PropTypes.func.isRequired,
  navigate: PropTypes.func.isRequired,
};

export default PipelineHeader;
