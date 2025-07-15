import React, { useState, useEffect, useRef } from "react"; // Add useRef
import PropTypes from "prop-types";
import { Box, Typography, TextField } from "@mui/material";
import DocumentSelector from "../../../components/generative/RAG/DocumentSelector";

export default function DocumentSelectionStep({
  documents: propDocumentIds, // Rename to reflect it's IDs
  setDocuments,
  setNextEnabled,
  sessionName,
  setSesssionName,
  sessionDescription,
  setSessionDescription,
}) {
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const initialLoadRef = useRef(true); // Ref to track initial render

  useEffect(() => {
    if (initialLoadRef.current && propDocumentIds && propDocumentIds.length > 0) {
      initialLoadRef.current = false;
    }
  }, [propDocumentIds]);


  useEffect(() => {
    const documentIdsSelected = selectedDocuments.length > 0;
    const validSessionName = sessionName.trim() !== "";
    setNextEnabled(documentIdsSelected && validSessionName);
  }, [selectedDocuments, sessionName, setNextEnabled]);

  useEffect(() => {
    const currentSelectedIds = selectedDocuments.map(doc => doc.id);
    if (JSON.stringify(currentSelectedIds.sort()) !== JSON.stringify(propDocumentIds.sort())) {
        setDocuments(currentSelectedIds);
    }
  }, [selectedDocuments, setDocuments, propDocumentIds]);


  const handleSessionNameChange = (event) => {
    setSesssionName(event.target.value);
  };

  const handleSessionDescriptionChange = (event) => {
    setSessionDescription(event.target.value);
  };

  const handleDocumentSelectionChange = (selectedDocs) => {
    setSelectedDocuments(selectedDocs);
  };

  return (
    <Box display="flex" flexDirection="column" height="100%" width="100%">
      <Box mb={3}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>Session Name</Typography>
        <TextField
          fullWidth
          variant="outlined"
          value={sessionName}
          onChange={handleSessionNameChange}
          placeholder="Enter session name"
          inputProps={{ maxLength: 256 }}
          margin="normal"
          error={sessionName.trim() === ""}
          helperText={sessionName.trim() === "" ? "Session name cannot be empty" : ""}
        />

        <Typography variant="subtitle1" sx={{ mb: 1 }}>Session Description</Typography>
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
          selectedIds={propDocumentIds || []}
          onSelect={handleDocumentSelectionChange}
        />
      </Box>
    </Box>
  );
}

DocumentSelectionStep.propTypes = {
  documents: PropTypes.arrayOf(PropTypes.string).isRequired,
  setDocuments: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  sessionName: PropTypes.string.isRequired,
  setSesssionName: PropTypes.func.isRequired,
  sessionDescription: PropTypes.string.isRequired,
  setSessionDescription: PropTypes.func.isRequired,
};