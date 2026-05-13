import { Box, Button, Dialog } from "@mui/material";
import { useEffect, useState, useCallback, useRef } from "react";
import PropTypes from "prop-types";
import AddIcon from "@mui/icons-material/AddCircleOutline";
import { useTranslation } from "react-i18next";
import SimplifiedDocumentTable from "./SimplifiedDocumentTable";
import Upload from "../../shared/Upload";
import { loadDocuments, addDocument, deleteDocument } from "../../../api/rag";

export default function DocumentSelector({
  selectedIds: initialSelectedIds = [],
  onSelect,
}) {
  const { t } = useTranslation(["generative"]);
  const [documents, setDocuments] = useState([]);
  const [selectedIds, setSelectedIds] = useState(initialSelectedIds);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);

  const previousSelectedIdsRef = useRef(JSON.stringify([...initialSelectedIds].map(String).sort()));

  const getNormalizedIdsKey = (ids) =>
    JSON.stringify([...ids].map(String).sort());

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
    if (getNormalizedIdsKey(selectedIds) !== getNormalizedIdsKey(initialSelectedIds)) {
      setSelectedIds([...initialSelectedIds]);
    }
  }, [initialSelectedIds]);

  useEffect(() => {
    // Only notify parent when selectedIds actually change
    const currentKey = getNormalizedIdsKey(selectedIds);
    if (currentKey !== previousSelectedIdsRef.current) {
      const selectedIdSet = new Set(selectedIds.map(String));
      const selectedDocs = documents.filter((doc) =>
        selectedIdSet.has(String(doc.id)),
      );
      onSelect?.(selectedDocs);
      previousSelectedIdsRef.current = currentKey;
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
      const uploadedDocuments = [];

      for (const file of fileList) {
        const docToAdd = {
          file,
          optional_metadata: {
            name: file.name,
            source: url || "local_upload",
          },
        };
        const savedDoc = await handleAddDocument(docToAdd);
        if (savedDoc) {
          uploadedDocuments.push(savedDoc);
        }
      }

      if (uploadedDocuments.length > 0) {
        setDocuments((prev) => {
          const nextDocs = [...uploadedDocuments, ...prev];
          return nextDocs.filter(
            (doc, index, array) =>
              index === array.findIndex((candidate) => candidate.id === doc.id),
          );
        });
        setSelectedIds((prev) => {
          const nextSelected = new Set(prev.map(String));
          uploadedDocuments.forEach((doc) => nextSelected.add(String(doc.id)));
          return Array.from(nextSelected);
        });
      }

      setUploadOpen(false);
    },
    [handleAddDocument],
  );

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
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

      <Box sx={{ width: "100%" }}>
        <Button
          variant="contained"
          fullWidth
          color="primary"
          size="large"
          startIcon={<AddIcon />}
          onClick={() => setUploadOpen(true)}
        >
          {t("generative:simplifiedRag.documents.uploadButton")}
        </Button>
      </Box>

      <Dialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            maxHeight: "80vh",
            minHeight: "300px",
            display: "flex",
            flexDirection: "column",
          },
        }}
      >
        <Box sx={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
          <Upload
            onFileUpload={handleFileUpload}
            multiple={true}
            emptyUploadText={t("generative:simplifiedRag.documents.emptyUploadText")}
          />
        </Box>
      </Dialog>
    </Box>
  );
}

DocumentSelector.propTypes = {
  selectedIds: PropTypes.arrayOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  ),
  onSelect: PropTypes.func,
};
