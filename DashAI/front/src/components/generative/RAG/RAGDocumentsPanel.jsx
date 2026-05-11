import React from "react";
import PropTypes from "prop-types";
import DocumentsBar from "./DocumentsBar";

/**
 * Unified RAG Documents Panel wrapper
 * Handles consistent DocumentsBar rendering across all RAG contexts
 * 
 * @param {string} selectedSessionId - Session ID for session-specific documents
 * @param {boolean} isRagChatActive - Whether RAG chat is currently active
 * @param {function} onDocumentChange - Optional callback for document changes
 */
export default function RAGDocumentsPanel({
  selectedSessionId,
  isRagChatActive = false,
  onDocumentChange,
  showSearch = false,
}) {
  return (
    <DocumentsBar
      selectedSessionId={selectedSessionId}
      taskName="RAGTask"
      onDocumentChange={onDocumentChange}
      showSearch={showSearch}
    />
  );
}

RAGDocumentsPanel.propTypes = {
  selectedSessionId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  isRagChatActive: PropTypes.bool,
  onDocumentChange: PropTypes.func,
  showSearch: PropTypes.bool,
};
