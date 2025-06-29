// RetrieverConfigurationStep.jsx
import React from "react";
import PropTypes from "prop-types";
import { Box } from "@mui/material";
import ComponentSelector from "../../../components/generative/RAG/ComponentSelector";
import { getRetrieverComponents } from "../../../api/rag";

function RetrieverConfigurationStep({ newSession, setNewSession, setNextEnabled }) {
  const handleConfigurationChange = (retrieverConfig) => {
    setNewSession(prev => ({
      ...prev,
      RAGParameters: {
        ...prev.RAGParameters,
        retrieval: retrieverConfig
      }
    }));
  };

  return (
    <Box sx={{ height: "100%", overflow: "auto" }}>
      <ComponentSelector
        componentType="Retriever"
        fetchComponents={getRetrieverComponents}
        initialValues={newSession.RAGParameters?.retrieval}
        onConfigurationChange={handleConfigurationChange}
        setNextEnabled={setNextEnabled}
      />
    </Box>
  );
}

RetrieverConfigurationStep.propTypes = {
  newSession: PropTypes.object.isRequired,
  setNewSession: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

export default RetrieverConfigurationStep;