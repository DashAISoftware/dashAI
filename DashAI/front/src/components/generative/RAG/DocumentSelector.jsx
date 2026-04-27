import { Box } from "@mui/material";
import { useEffect, useState, useCallback, useRef } from "react"; // Added useRef
import PropTypes from "prop-types";
import SimplifiedDocumentTable from "./SimplifiedDocumentTable";
import Upload from "../../shared/Upload";
import { loadDocuments, addDocument, deleteDocument } from "../../../api/rag";

export default function DocumentSelector({
  selectedIds: initialSelectedIds = [],
  onSelect,
}) {
  const [documents, setDocuments] = useState([]);
  const [selectedIds, setSelectedIds] = useState(initialSelectedIds);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadKey, setUploadKey] = useState(0);

  const previousSelectedIdsRef = useRef(initialSelectedIds);

  useEffect(() => {
    const fetchDocuments = async () => {
      setIsLoading(true);
      try {
        const docs = await loadDocuments();
        // Sort documents by creation date, newest first
        const sortedDocs = docs.sort((a, b) => {
          const dateA = new Date(a.created);
          const dateB = new Date(b.created);
          return dateB - dateA; // Descending order (newest first)
        });
        setDocuments(sortedDocs);
      } catch (error) {
        console.error("Failed to load documents:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDocuments();
  }, []);

  useEffect(() => {
    // Sync selectedIds with incoming initialSelectedIds only if they're different
    if (
      JSON.stringify(selectedIds.sort()) !==
      JSON.stringify(initialSelectedIds.sort())
    ) {
      setSelectedIds(initialSelectedIds);
    }
  }, [initialSelectedIds]);

  useEffect(() => {
    // Only notify parent when selectedIds actually change
    if (
      JSON.stringify(selectedIds.sort()) !==
      JSON.stringify(previousSelectedIdsRef.current.sort())
    ) {
      const selectedDocs = documents.filter((doc) =>
        selectedIds.includes(doc.id),
      );
      onSelect(selectedDocs);
      previousSelectedIdsRef.current = [...selectedIds]; // Create a new array
    }
  }, [selectedIds, documents, onSelect]);

  const handleToggleSelection = useCallback((id) => {
    setSelectedIds((prev) => {
      const newSelected = prev.includes(id)
        ? prev.filter((x) => x !== id)
        : [...prev, id];
      return newSelected;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedIds(documents.map((doc) => doc.id));
  }, [documents]);

  const handleDeselectAll = useCallback(() => {
    setSelectedIds([]);
  }, []);

  const handleAddDocument = useCallback(async (newDoc) => {
    try {
      const savedDoc = await addDocument(newDoc);
      setDocuments((prev) => [savedDoc, ...prev]);
      setSelectedIds((prev) => [...prev, savedDoc.id]);
      setUploadKey((prev) => prev + 1);
      return savedDoc;
    } catch (error) {
      console.error("Failed to add document:", error);
      return null;
    }
  }, []);

  const handleRemoveDocument = useCallback(async (id) => {
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((doc) => doc.id !== id));
      setSelectedIds((prev) => prev.filter((x) => x !== id));
    } catch (error) {
      console.error("Failed to delete document:", error);
    }
  }, []);

  const handleFileUpload = useCallback(
    async (files, url) => {
      if (!files) return;

      console.log("Files to upload at handleFileUpload:", files);

      const fileList = Array.isArray(files) ? files : [files];

      for (const file of fileList) {
        const docToAdd = {
          file,
          optional_metadata: {
            name: file.name,
            source: url || "local_upload",
          },
        };
        await handleAddDocument(docToAdd);
      }
    },
    [handleAddDocument],
  );

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
        gap: 2,
        width: "100%",
      }}
    >
      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <SimplifiedDocumentTable
          documents={documents.map((doc) => ({
            ...doc,
            preview: doc.file_url,
            file_type: doc.file_name.split(".").pop().toLowerCase(),
          }))}
          selectedIds={selectedIds}
          onToggle={handleToggleSelection}
          onRemove={handleRemoveDocument}
          isLoading={isLoading}
        />
      </Box>

      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <Upload
          key={uploadKey}
          onFileUpload={handleFileUpload}
          multiple={true}
        />
      </Box>
    </Box>
  );
}

DocumentSelector.propTypes = {
  selectedIds: PropTypes.arrayOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  ),
  onSelect: PropTypes.func,
};
