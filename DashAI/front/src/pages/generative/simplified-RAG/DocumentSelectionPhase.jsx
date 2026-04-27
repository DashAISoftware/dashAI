import { useState, useEffect } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  CircularProgress,
} from "@mui/material";
import CenterBox from "../../../components/threeSectionLayout/panelContainers/CenterBox";
import DocumentSelector from "../../../components/generative/RAG/DocumentSelector";
import { useTranslation } from "react-i18next";

export default function DocumentSelectionPhase({ onNext }) {
  const { t } = useTranslation(["generative", "common"]);
  const [sessionName, setSessionName] = useState("");
  const [sessionDescription, setSessionDescription] = useState("");
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [nameError, setNameError] = useState("");

  const isValid = sessionName.trim() !== "" && selectedDocuments.length > 0;

  const handleDocumentSelectionChange = (selectedDocs) => {
    setSelectedDocuments(selectedDocs);
  };

  const handleSessionNameChange = (event) => {
    const value = event.target.value;
    setSessionName(value);
    if (value.trim() === "") {
      setNameError("Session name cannot be empty");
    } else {
      setNameError("");
    }
  };

  const handleSessionDescriptionChange = (event) => {
    setSessionDescription(event.target.value);
  };

  const handleNext = () => {
    if (!isValid) return;

    onNext({
      name: sessionName.trim(),
      description: sessionDescription.trim(),
      documents: selectedDocuments.map((doc) => doc.id),
    });
  };

  return (
    <CenterBox>
      <Box
        display="flex"
        flexDirection="column"
        gap={3}
        width="100%"
      >
        {/* Header */}
        <Box>
          <Typography variant="h5" component="h1" sx={{ mb: 1 }}>
            Create RAG Session - Step 1: Basic Information
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Start by providing a name, optional description, and selecting the documents
            you want to use for this RAG session.
          </Typography>
        </Box>

        {/* Session Details */}
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 3, fontWeight: 600 }}>
            Session Details
          </Typography>

          <Box display="flex" flexDirection="column" gap={2}>
            <TextField
              fullWidth
              label="Session Name *"
              variant="outlined"
              value={sessionName}
              onChange={handleSessionNameChange}
              placeholder="e.g., Product Documentation RAG"
              error={Boolean(nameError)}
              helperText={nameError}
              inputProps={{ maxLength: 256 }}
              size="medium"
            />

            <TextField
              fullWidth
              label="Description (Optional)"
              variant="outlined"
              value={sessionDescription}
              onChange={handleSessionDescriptionChange}
              placeholder="Describe the purpose of this RAG session..."
              multiline
              rows={3}
              inputProps={{ maxLength: 512 }}
              size="medium"
            />
          </Box>
        </Box>

        {/* Document Selection */}
        <Box display="flex" flexDirection="column" gap={1}>
          <Typography variant="subtitle1">
            Select Documents
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Upload new documents or select from existing ones to be used for RAG.
          </Typography>

          <Box
            width="100%"
            sx={{
              display: "flex",
              flexDirection: "column",
              minHeight: "500px",
            }}
          >
            <DocumentSelector
              key={`doc-selector-${JSON.stringify(selectedDocuments.map((d) => d.id) || [])}`}
              selectedIds={selectedDocuments.map((d) => d.id)}
              onSelect={handleDocumentSelectionChange}
            />
          </Box>
        </Box>

        {/* Actions */}
        <Box
          display="flex"
          justifyContent="flex-end"
          gap={2}
          sx={{ pt: 2, borderTop: "1px solid", borderColor: "divider" }}
        >
          <Button variant="outlined" color="inherit">
            Close
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handleNext}
            disabled={!isValid}
          >
            Next
          </Button>
        </Box>
      </Box>
    </CenterBox>
  );
}
