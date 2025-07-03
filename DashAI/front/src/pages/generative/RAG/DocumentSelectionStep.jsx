import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";
import DocumentSelector from "../../../components/generative/RAG/DocumentSelector"; // Adjust the import path as needed






// Helper function to convert document paths to UI-friendly objects
const createDocumentObjectFromPath = (path) => ({
  id: path,
  name: path.split('/').pop() || path, // Use filename as name, fallback to full path
  updatedAt: new Date().toISOString(), // Initial timestamp for new paths
});

export default function DocumentSelectionStep({ documents, setDocuments, setNextEnabled }) {
  // Initialize localDocumentObjects and selectedObjectIds once from the 'documents' prop.
  // This runs only on the initial mount.
  const [localDocumentObjects, setLocalDocumentObjects] = useState(() => {
    const initialLocalDocs = documents.map(createDocumentObjectFromPath);
    const initialSelectedIds = documents; // Paths are directly the IDs
    return initialLocalDocs;
  });

  const [selectedObjectIds, setSelectedObjectIds] = useState(() => {
    return documents; // Paths are directly the IDs
  });

  // Effect 1: Sync selectedObjectIds (paths) back to the parent component
  // This effect ensures the parent's 'documents' prop is updated when local selection changes.
  useEffect(() => {
    // Only update parent if there's a change to prevent infinite loops and unnecessary re-renders
    if (JSON.stringify(selectedObjectIds) !== JSON.stringify(documents)) {
      setDocuments(selectedObjectIds); // selectedObjectIds already contains the paths
    }
  }, [selectedObjectIds, setDocuments, documents]); // Dependencies: local selected IDs, and parent's setter/prop for comparison

  // Effect 2: Notify parent about step validity
  // This effect ensures the 'Next' button's enabled state is correct.
  useEffect(() => {
    const isValid = selectedObjectIds && selectedObjectIds.length > 0;
    setNextEnabled(isValid);
  }, [selectedObjectIds, setNextEnabled]); // Dependencies: local selected IDs, and parent's setter

  // Handler for when DocumentSelector's selection changes (checkboxes)
  const handleDocumentSelectionChange = useCallback((selectedDocs) => {
    // Extract 'id' (which is the path) from the selected document objects
    const newSelectedIds = selectedDocs.map(doc => doc.id);
    setSelectedObjectIds(newSelectedIds);
  }, []);

  // Handler for when DocumentSelector adds a new document (e.g., from Upload component)
  const handleAddDocumentObject = useCallback((newDoc) => {
    setLocalDocumentObjects(prev => {
      // Ensure no duplicates based on ID (path) before adding
      if (!prev.some(doc => doc.id === newDoc.id)) {
        const updatedDocs = [...prev, newDoc];
        // Also ensure it's selected in the UI
        setSelectedObjectIds(currentSelected => {
          if (!currentSelected.includes(newDoc.id)) {
            return [...currentSelected, newDoc.id];
          }
          return currentSelected;
        });
        return updatedDocs;
      }
      return prev;
    });
  }, []);

  // Handler for when DocumentSelector removes a document
  const handleRemoveDocumentObject = useCallback((docId) => {
    setLocalDocumentObjects(prev => prev.filter(doc => doc.id !== docId));
    setSelectedObjectIds(prev => prev.filter(id => id !== docId));
  }, []);


  return (
    <Box display="flex" flexDirection="column" height="100%" width="100%">
      <Typography variant="h6" sx={{ mb: 2 }}>Select Documents</Typography>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
        Upload new documents or select from existing ones to be used for RAG.
      </Typography>

      {/* Integrate the DocumentSelector component */}
      <Box flexGrow={1}> {/* Allow DocumentSelector to take available height */}
        <DocumentSelector
          documents={localDocumentObjects} // Pass the processed document objects
          selected={selectedObjectIds}   // Pass the selected IDs (paths)
          onSelect={handleDocumentSelectionChange} // Callback when selection changes
          onAddDocument={handleAddDocumentObject}  // Callback for new document added
          onRemove={handleRemoveDocumentObject}    // Callback for document removal
        />
      </Box>
    </Box>
  );
}

DocumentSelectionStep.propTypes = {
  documents: PropTypes.arrayOf(PropTypes.string).isRequired,
  setDocuments: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};
