import React, { useState } from "react";
import { Box } from "@mui/material";
import DocumentListItem from "./DocumentListItem";

export default function DocumentList({ documents, onDocumentClick }) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        minWidth: 0,
      }}
    >
      {documents.map((document) => (
        <DocumentListItem
          key={document.id}
          document={document}
          disabled={false}
          onClick={() => onDocumentClick && onDocumentClick(document)}
        />
      ))}
    </Box>
  );
}
