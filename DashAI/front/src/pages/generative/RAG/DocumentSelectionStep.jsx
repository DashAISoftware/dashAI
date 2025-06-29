import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { Box, CircularProgress } from "@mui/material";
import DocumentSelector from "../../../components/generative/RAG/DocumentSelector";
import SessionMetadata from "../../../components/generative/RAG/SessionMetadata";

function DocumentSelectionStep({ newSession, setNewSession, setNextEnabled }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch available documents on component mount
  useEffect(() => {
    const fetchDocuments = async () => {
      setLoading(true);
      try {
        // Replace this with your actual API call to get documents
        // For now using a mock response with delay
        await new Promise(resolve => setTimeout(resolve, 500));
        const data = [
          { id: 1, name: "Product Documentation.pdf", type: "PDF", size: "1.2 MB", updatedAt: "2025-05-15" },
          { id: 2, name: "User Manual.docx", type: "DOCX", size: "3.4 MB", updatedAt: "2025-05-20" },
          { id: 3, name: "API Reference.pdf", type: "PDF", size: "2.1 MB", updatedAt: "2025-06-01" },
          { id: 4, name: "Technical Specifications.txt", type: "TXT", size: "4.7 MB", updatedAt: "2025-06-10" },
          { id: 5, name: "Troubleshooting Guide.pdf", type: "PDF", size: "1.8 MB", updatedAt: "2025-06-15" }
        ];
        setDocuments(data);
      } catch (error) {
        console.error("Failed to fetch documents:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, []);

  // Update next button state whenever documents or session name changes
  useEffect(() => {
    const hasDocuments = newSession.documents && newSession.documents.length > 0;
    const hasName = Boolean(newSession.name);
    setNextEnabled(hasDocuments && hasName);
  }, [newSession.documents, newSession.name, setNextEnabled]);

  const handleSessionMetadataUpdate = (metadata) => {
    setNewSession(prev => ({
      ...prev,
      name: metadata.name,
      description: metadata.description
    }));
  };

  const handleDocumentsSelect = (selectedDocuments) => {
    setNewSession(prev => ({
      ...prev,
      documents: selectedDocuments
    }));
  };

  return (
    <Box 
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"auto"}
    >
      <SessionMetadata 
        sessionData={newSession}
        onUpdate={handleSessionMetadataUpdate}
        setNextEnabled={setNextEnabled}
      />
      
      {loading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : (
        <DocumentSelector
          selected={newSession.documents || []}  // Match the expected prop name
          onSelect={handleDocumentsSelect}        // Match the expected prop name
        />
      )}
    </Box>
  );
}

DocumentSelectionStep.propTypes = {
  newSession: PropTypes.object.isRequired,
  setNewSession: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

export default DocumentSelectionStep;