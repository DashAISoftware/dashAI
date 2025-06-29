import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { Box } from "@mui/material";
import FormSchemaWithSelectedModel from "../../../components/shared/FormSchemaWithSelectedModel";

function ModelConfigurationStep({
  taskName,
  initialParameters = {},
  onConfigurationChange,
  setNextEnabled
}) {
  const [parameters, setParameters] = useState(initialParameters);
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    if (Object.keys(parameters).length > 0) {
      onConfigurationChange(parameters);
      setIsConfigured(true);
    }
  }, [parameters, onConfigurationChange]);

  useEffect(() => {
    setNextEnabled(isConfigured);
  }, [isConfigured, setNextEnabled]);

  const handleFormSubmit = (values) => {
    setParameters(values);
    setIsConfigured(true);
  };

  return (
    <Box sx={{ height: "100%", overflow: "auto" }}>
      <FormSchemaWithSelectedModel
        modelToConfigure={taskName}
        initialValues={parameters}
        onFormSubmit={handleFormSubmit}
        onCancel={() => {}}
      />
    </Box>
  );
}

ModelConfigurationStep.propTypes = {
  taskName: PropTypes.string.isRequired,
  initialParameters: PropTypes.object,
  onConfigurationChange: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

export default ModelConfigurationStep;