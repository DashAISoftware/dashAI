import React, { useState } from "react";
import {
  Box,
  Checkbox,
  IconButton,
  Tooltip,
  Typography,
  Paper,
  CircularProgress,
} from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import DeleteIcon from "@mui/icons-material/Delete";
import PropTypes from "prop-types";
import { formatDate } from "../../../utils";
import DocumentPreviewModal from "./DocumentPreviewModal";

export default function SimplifiedDocumentTable({
  documents,
  selectedIds,
  onToggle,
  onRemove,
  isLoading = false,
}) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [txtContent, setTxtContent] = useState("");

  const handleOpenPreview = async (doc) => {
    setPreviewDoc(doc);
    if (doc.file_type === "txt" && doc.preview) {
      try {
        const res = await fetch(doc.preview);
        const text = await res.text();
        setTxtContent(text);
      } catch (e) {
        setTxtContent("Error loading TXT file");
      }
    }
    setPreviewOpen(true);
  };

  const handleClosePreview = () => {
    setPreviewOpen(false);
    setPreviewDoc(null);
    setTxtContent("");
  };

  return (
    <>
      <Paper
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          width: "100%",
          borderRadius: 2,
          backgroundColor: "background.paper",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "50px 1fr 150px 120px",
            gap: 2,
            p: 2,
            borderBottom: "1px solid",
            borderColor: "divider",
            backgroundColor: "action.hover",
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          <Box>
            <Checkbox
              checked={
                documents.length > 0 &&
                selectedIds.length === documents.length
              }
              indeterminate={
                selectedIds.length > 0 &&
                selectedIds.length < documents.length
              }
              onChange={(e) => {
                if (e.target.checked) {
                  documents.forEach((doc) => {
                    if (!selectedIds.includes(doc.id)) {
                      onToggle(doc.id);
                    }
                  });
                } else {
                  selectedIds.forEach((id) => onToggle(id));
                }
              }}
            />
          </Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Name
          </Typography>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Added On
          </Typography>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Actions
          </Typography>
        </Box>

        {/* Rows Container */}
        <Box
          sx={{
            flex: 1,
            overflow: "auto",
            minHeight: 0,
            "&::-webkit-scrollbar": {
              width: "8px",
            },
            "&::-webkit-scrollbar-track": {
              backgroundColor: "#252836",
            },
            "&::-webkit-scrollbar-thumb": {
              backgroundColor: "#374151",
              borderRadius: "4px",
              "&:hover": {
                backgroundColor: "#4a5568",
              },
            },
          }}
        >
          {isLoading ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
              }}
            >
              <CircularProgress />
            </Box>
          ) : documents.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                color: "text.secondary",
              }}
            >
              <Typography>No documents available</Typography>
            </Box>
          ) : (
            documents.map((doc) => (
              <Box
                key={doc.id}
                sx={{
                  display: "grid",
                  gridTemplateColumns: "50px 1fr 150px 120px",
                  gap: 2,
                  p: 2,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  alignItems: "center",
                  backgroundColor: selectedIds.includes(doc.id)
                    ? "action.selected"
                    : "inherit",
                  "&:hover": {
                    backgroundColor: "action.hover",
                  },
                }}
              >
                <Checkbox
                  checked={selectedIds.includes(doc.id)}
                  onChange={() => onToggle(doc.id)}
                />
                <Typography
                  variant="body2"
                  sx={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {doc.file_name}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  {formatDate(doc.created)}
                </Typography>
                <Box sx={{ display: "flex", gap: 1 }}>
                  <Tooltip title="Preview">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenPreview(doc)}
                    >
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton
                      size="small"
                      onClick={() => onRemove(doc.id)}
                      color="error"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Box>
            ))
          )}
        </Box>
      </Paper>

      <DocumentPreviewModal
        open={previewOpen}
        onClose={handleClosePreview}
        document={previewDoc}
        txtContent={txtContent}
      />
    </>
  );
}

SimplifiedDocumentTable.propTypes = {
  documents: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      file_name: PropTypes.string.isRequired,
      created: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.instanceOf(Date),
      ]).isRequired,
      preview: PropTypes.string,
      file_type: PropTypes.string,
    }),
  ).isRequired,
  selectedIds: PropTypes.arrayOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  ).isRequired,
  onToggle: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
};
