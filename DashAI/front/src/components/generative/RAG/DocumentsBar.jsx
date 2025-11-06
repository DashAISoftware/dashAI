import { useEffect, useState } from "react";
import { Box, Typography } from "@mui/material";
import SearchBar from "../../threeSectionLayout/SearchBar";
import DocumentList from "./DocumentList";
import { useSnackbar } from "notistack";
import { getSessionDocuments } from "../../../api/rag";

export default function DocumentsBar({ selectedSessionId, taskName }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [documents, setDocuments] = useState([]);
  const [filteredDocuments, setFilteredDocuments] = useState([]);
  const { enqueueSnackbar } = useSnackbar();

  // Fetch documents for the selected RAG session
  useEffect(() => {
    const fetchDocuments = async () => {
      if (!selectedSessionId) {
        setDocuments([]);
        return;
      }

      try {
        const data = await getSessionDocuments(selectedSessionId);

        // Transform API response to component format
        const transformedDocuments = data.map((doc) => ({
          id: doc.id,
          name: doc.file_name,
          type: doc.file_type,
          uploadedAt: doc.created,
          file_name: doc.file_name,
          file_type: doc.file_type,
          preview: doc.file_url,
          created: doc.created,
          optional_metadata: doc.optional_metadata,
        }));

        setDocuments(transformedDocuments);
        setFilteredDocuments(transformedDocuments);
      } catch (error) {
        enqueueSnackbar("Failed to fetch documents", {
          variant: "error",
        });
        console.error("Failed to fetch documents:", error);
      }
    };

    fetchDocuments();
  }, [selectedSessionId, enqueueSnackbar]);

  // Filter documents based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredDocuments(documents);
      return;
    }

    const filtered = documents.filter((doc) =>
      doc.name.toLowerCase().includes(searchQuery.toLowerCase()),
    );
    setFilteredDocuments(filtered);
  }, [searchQuery, documents]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        height: "100%",
        width: "100%",
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: "1px solid #333", flexShrink: 0 }}>
        <Typography variant="h6">Documents</Typography>
        <Typography variant="caption" sx={{ color: "rgb(113, 113, 122)" }}>
          {filteredDocuments.length} document
          {filteredDocuments.length !== 1 ? "s" : ""}
        </Typography>
      </Box>

      {/* Search bar */}
      <Box sx={{ p: 2, borderBottom: "1px solid #333", flexShrink: 0 }}>
        <SearchBar
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onClear={() => setSearchQuery("")}
          placeholder="Search documents"
        />
      </Box>

      {/* Document list */}
      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          overflowX: "hidden",
          p: 2,
          minWidth: 0,
        }}
      >
        {filteredDocuments.length > 0 ? (
          <DocumentList documents={filteredDocuments} />
        ) : (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              p: 2,
            }}
          >
            <Typography
              variant="body2"
              sx={{ color: "text.secondary", textAlign: "center" }}
            >
              {searchQuery
                ? "No documents found"
                : "No documents in this session"}
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
}
