import { Box } from "@mui/material";
import { useEffect, useState } from "react";
import PropTypes from "prop-types"; // Import PropTypes
import DocumentTable from "./DocumentTable";
import Upload from "../../shared/Upload"; // Assuming path is correct

export default function DocumentSelector({
  documents: initialDocuments = [], // Renamed prop for clarity, uses initial state
  selected: initialSelectedIds = [], // Renamed prop for clarity
  onSelect, // Callback for when selection changes (receives selected document objects)
  onAddDocument, // Callback for when a new document object is added (receives new doc object)
  onRemove, // Callback for when a document is removed (receives docId/path)
}) {
  const [documents, setDocuments] = useState(initialDocuments);
  const [selectedIds, setSelectedIds] = useState(initialSelectedIds);
  // Add a key state to force Upload component re-render
  const [uploadKey, setUploadKey] = useState(0);

  // Sync internal 'documents' state with 'initialDocuments' prop
  useEffect(() => {
    setDocuments(initialDocuments);
  }, [initialDocuments]);

  // Sync internal 'selectedIds' state with 'initialSelectedIds' prop
  useEffect(() => {
    setSelectedIds(initialSelectedIds);
  }, [initialSelectedIds]);

  // Sync selected documents with parent's onSelect callback
  useEffect(() => {
    const selectedDocs = documents.filter(doc => selectedIds.includes(doc.id));
    if (onSelect) {
      onSelect(selectedDocs);
    }
  }, [selectedIds, documents, onSelect]);

  const handleToggleSelection = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    setSelectedIds(documents.map(doc => doc.id));
  };

  const handleDeselectAll = () => {
    setSelectedIds([]);
  };

  // Internal handler for adding a document object (before notifying parent)
  const addDocumentObject = (newDoc) => {
    setDocuments(prev => {
      // Ensure no duplicates based on ID (path)
      if (!prev.some(doc => doc.id === newDoc.id)) {
        return [newDoc, ...prev]; // Add to the beginning
      }
      return prev;
    });
    // Call the parent's onAddDocument callback
    if (onAddDocument) {
      onAddDocument(newDoc);
    }
  };

  // Internal handler for removing a document object (before notifying parent)
  const removeDocumentObject = (id) => {
    setDocuments(prev => prev.filter(doc => doc.id !== id));
    setSelectedIds(prev => prev.filter(x => x !== id));
    // Call the parent's onRemove callback
    if (onRemove) {
      onRemove(id);
    }
  };

  const handleFileUpload = (file, url) => {
    if (!file) return;

    // The 'id' of the document will be the URL (or file.name if no URL is available)
    // This allows the 'id' to directly represent the path/reference
    const docId = url || file.name;

    const newDoc = {
      id: docId,
      name: file.name,
      updatedAt: new Date().toISOString(),
      preview: url, // Store URL for preview if available
    };

    addDocumentObject(newDoc); // Use the internal handler
    setSelectedIds(prev => [...prev, newDoc.id]); // Also select it upon upload

    // Reset the upload component by incrementing its key
    setUploadKey(prev => prev + 1);
  };

  return (
    <Box display="flex" gap={2} height="100%">
      <Box width="65%">
        <DocumentTable
          documents={documents}
          selectedIds={selectedIds}
          onToggle={handleToggleSelection}
          onSelectAll={handleSelectAll}
          onDeselectAll={handleDeselectAll}
          onRemove={removeDocumentObject} // Use the internal removal handler
        />
      </Box>

      <Box width="35%">
        <Upload
          key={uploadKey}
          onFileUpload={handleFileUpload}
        />
      </Box>
    </Box>
  );
}

DocumentSelector.propTypes = {
  documents: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    updatedAt: PropTypes.string.isRequired,
    preview: PropTypes.string, // Optional
  })),
  selected: PropTypes.arrayOf(PropTypes.string), // Array of document IDs (paths)
  onSelect: PropTypes.func, // (selectedDocs: array of objects) => void
  onAddDocument: PropTypes.func, // (newDoc: object) => void
  onRemove: PropTypes.func, // (docId: string) => void
};
