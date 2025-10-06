import React from "react";
import PropTypes from "prop-types";
import { Box } from "@mui/material";
import ComponentSelector from "../../../../components/generative/RAG/ComponentSelector";
import { getGeneratorComponents } from "../../../../api/rag";

function AlgorithmConfigurationStep({
  newSession,
  setNewSession,
  setNextEnabled,
}) {
  const handleConfigurationChange = (generatorConfig) => {
    setNewSession((prev) => ({
      ...prev,
      RAGParameters: {
        ...prev.RAGParameters,
        generation: generatorConfig,
      },
    }));
  };

  return (
    <Box sx={{ height: "100%", overflow: "auto" }}>
      <ComponentSelector
        componentType="Generator"
        fetchComponents={getGeneratorComponents}
        initialValues={newSession.RAGParameters?.generation}
        onConfigurationChange={handleConfigurationChange}
        setNextEnabled={setNextEnabled}
      />
    </Box>
  );
}

AlgorithmConfigurationStep.propTypes = {
  newSession: PropTypes.object.isRequired,
  setNewSession: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

export default AlgorithmConfigurationStep;
