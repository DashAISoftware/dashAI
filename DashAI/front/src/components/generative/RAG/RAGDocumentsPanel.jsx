import React from "react";
import PropTypes from "prop-types";
import DocumentsBar from "./DocumentsBar";

/**
 * Unified RAG Documents Panel wrapper.
 * Handles consistent DocumentsBar rendering across all RAG contexts.
 *
 * @param {object}   props
 * @param {string}   [props.selectedSessionId] - Session ID for session-specific documents.
 * @param {boolean}  [props.isRagChatActive=false] - Whether RAG chat is currently active.
 * @param {function} [props.onDocumentChange] - Optional callback for document changes.
 * @param {boolean}  [props.showSearch=false] - Whether to show the search bar.
 * @returns {JSX.Element} The DocumentsBar component.
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
