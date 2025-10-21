import React, { useEffect } from "react";
import { Box, Typography } from "@mui/material";
import PropTypes from "prop-types";

export default function PromptConfigurationStep({
  sessionData,
  setSessionData,
  setNextEnabled,
}) {
  // Set this step as always valid
  useEffect(() => {
    if (setNextEnabled) {
      setNextEnabled(true);
    }
  }, [setNextEnabled]);

  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      height="400px"
      p={3}
    >
      <Typography variant="h6" color="text.primary" gutterBottom>
        Prompt Configuration
      </Typography>
      <Typography variant="body2" color="text.secondary" textAlign="center">
        This step is currently under development. The default prompt template
        will be used.
      </Typography>
      <Box
        mt={3}
        p={2}
        sx={{
          backgroundColor: "action.hover",
          borderRadius: 1,
          maxWidth: "600px",
        }}
      >
        <Typography variant="caption" color="text.secondary">
          Default template:
        </Typography>
        <Typography variant="body2" sx={{ mt: 1, fontFamily: "monospace" }}>
          Answer to this message: {"{input}"}, with the following information:{" "}
          {"{chunks}"}
        </Typography>
      </Box>
    </Box>
  );
}

PromptConfigurationStep.propTypes = {
  sessionData: PropTypes.object.isRequired,
  setSessionData: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func,
};
