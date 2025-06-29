import { Box } from "@mui/material";
import { useEffect, useState } from "react";
import DocumentTable from "./DocumentTable";
import Upload from "../../shared/Upload";

export default function DocumentSelector({ 
  selected = [],  // Provide default empty array to prevent map errors
  onSelect
}) {
  const [documents, setDocuments] = useState([]);
  const [selectedIds, setSelectedIds] = useState(
    (selected || []).map(doc => doc.id)
  );
  // Add a key state to force Upload component re-render
  const [uploadKey, setUploadKey] = useState(0);

  // Fetch documents on mount
  useEffect(() => {
    // Simulated API
    const fetchDocuments = async () => {
      // Return mock data if needed
      return [
        { id: "doc1", name: "Document 1", updatedAt: new Date().toISOString() },
        { id: "doc2", name: "Document 2", updatedAt: new Date().toISOString() }
      ];
    };
    
    fetchDocuments().then(setDocuments);
  }, []);

  // Sync selected documents with parent
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

  const handleAddDocument = (newDoc) => {
    const newDocWithId = {
      ...newDoc,
      id: `doc-${Date.now()}`,
      updatedAt: new Date().toISOString()
    };
    
    setDocuments(prev => [newDocWithId, ...prev]);
    setSelectedIds(prev => [...prev, newDocWithId.id]);
  };

  const handleRemove = (id) => {
    setDocuments(prev => prev.filter(doc => doc.id !== id));
    setSelectedIds(prev => prev.filter(x => x !== id));
  };

  const handleFileUpload = (file, url) => {
    if (!file) return;
    
    const newDoc = {
      id: `doc-${Date.now()}`,
      name: file.name,
      updatedAt: new Date().toISOString(),
      preview: url
    };
    
    handleAddDocument(newDoc);
    
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
          onRemove={handleRemove}
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