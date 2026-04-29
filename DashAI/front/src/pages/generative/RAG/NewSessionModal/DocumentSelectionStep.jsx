import React, { useCallback, useEffect } from "react";
import PropTypes from "prop-types";
import { Box, Typography, TextField } from "@mui/material";
import DocumentSelector from "../../../../components/generative/RAG/DocumentSelector";

export default function DocumentSelectionStep({
  documents: propDocumentIds,
  setDocuments,
  setNextEnabled,
  sessionName,
  setSesssionName,
  sessionDescription,
  setSessionDescription,
}) {
  useEffect(() => {
    const hasSelectedDocuments = propDocumentIds && propDocumentIds.length > 0;
    const validSessionName = sessionName.trim() !== "";
    setNextEnabled(hasSelectedDocuments && validSessionName);
  }, [propDocumentIds, sessionName]);

  const handleDocumentSelectionChange = useCallback((selectedDocs) => {
    const selectedIds = selectedDocs.map((doc) => doc.id);
    setDocuments(selectedIds);
  }, [setDocuments]);

  const handleSessionNameChange = (event) => {
    setSesssionName(event.target.value);
  };

  const handleSessionDescriptionChange = (event) => {
    setSessionDescription(event.target.value);
  };

  return (
    <Box display="flex" flexDirection="column" height="100%" width="100%">
      <Box mb={3}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Session Name
        </Typography>
        <TextField
          fullWidth
          variant="outlined"
          value={sessionName}
          onChange={handleSessionNameChange}
          placeholder="Enter session name"
          inputProps={{ maxLength: 256 }}
          margin="normal"
          error={sessionName.trim() === ""}
          helperText={
            sessionName.trim() === "" ? "Session name cannot be empty" : ""
          }
        />

        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Session Description
        </Typography>
        <TextField
          fullWidth
          variant="outlined"
          value={sessionDescription}
          onChange={handleSessionDescriptionChange}
          placeholder="Enter session description"
          inputProps={{ maxLength: 512 }}
          margin="normal"
          multiline
          rows={3}
        />
      </Box>

      <Typography variant="h6">Select Documents</Typography>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
        Upload new documents or select from existing ones to be used for RAG.
      </Typography>

      <Box flexGrow={1}>
        <DocumentSelector
          key={`doc-selector-${JSON.stringify(propDocumentIds || [])}`}
          selectedIds={propDocumentIds || []}
          onSelect={handleDocumentSelectionChange}
        />
      </Box>
    </Box>
  );
}

DocumentSelectionStep.propTypes = {
  documents: PropTypes.arrayOf(PropTypes.number).isRequired,
  setDocuments: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  sessionName: PropTypes.string.isRequired,
  setSesssionName: PropTypes.func.isRequired,
  sessionDescription: PropTypes.string.isRequired,
  setSessionDescription: PropTypes.func.isRequired,
};
