import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Typography } from "@mui/material";
import SessionBar from "../../../components/generative/SessionBar";
import MainGenerativeBox from "../../../components/generative/MainGenerativeBox";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import DocumentTable from "../../../components/generative/RAG/DocumentTable";
import {
  loadDocuments,
  deleteDocument,
} from "../../../api/rag";
import { getSessions, removeSession } from "../../../api/session";
import CenterBox from "../../../components/threeSectionLayout/panelContainers/CenterBox";

function RAGDocumentsPage() {
  const navigate = useNavigate();
  const [allDocuments, setAllDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [sessions, setSessions] = useState([]);

  const loadSessions = useCallback(async () => {
    try {
      const allSessions = await getSessions();
      setSessions(allSessions);
    } catch (error) {
      console.error("RAGDocumentsPage: Error loading sessions:", error);
    }
  }, []);

  const fetchAllDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    try {
      const docs = await loadDocuments();
      setAllDocuments(docs);
    } catch (error) {
      console.error("RAGDocumentsPage: Error loading all documents:", error);
    } finally {
      setDocumentsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
    fetchAllDocuments();
  }, [loadSessions, fetchAllDocuments]);

  const handleRemoveDocumentFromTable = useCallback(
    async (id) => {
      try {
        await deleteDocument(id);
        await fetchAllDocuments();
      } catch (error) {
        console.error("RAGDocumentsPage: Failed to delete document:", error);
      }
    },
    [fetchAllDocuments],
  );

  const handleAddDocument = useCallback((newDoc) => {
    setAllDocuments((prev) => [newDoc, ...prev]);
  }, []);

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    // Navigate directly to generative with session
    navigate("/app/generative", { 
      state: { 
        selectedSessionId: sessionId,
        selectedTaskName: taskName,
        selectedDisplayName: taskDisplayName
      } 
    });
  };

  const handleNewSessionButton = () => {
    // Navigate to generative with no session selected
    navigate("/app/generative");
  };

  const handleSessionDelete = async (id) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    await removeSession(id);
  };

  return (
    <Box height="calc(100vh - 74px)" width="100%" display="flex">
      <Box width="20%">
        <SessionBar
          sessions={sessions}
          handleSessionClick={handleSessionClick}
          handleNewSessionButton={handleNewSessionButton}
          handleSessionDelete={handleSessionDelete}
          stepIndex={0}
          showSearch={false}
        />
      </Box>

      <Box width="60%">
        <CenterBox>
            <RAGBreadcrumbs />
            <Typography variant="h5" component="h1">
              RAG Documents
            </Typography>
            <Typography variant="subtitle1" component="p" sx={{ mb: 2 }}>
              Manage documents for your RAG sessions: view existing documents and upload new ones to enhance your AI knowledge base.
            </Typography>

            <DocumentTable
              documents={[...allDocuments]
                .sort(
                  (a, b) =>
                    new Date(b.created || b.createdAt || 0) -
                    new Date(a.created || a.createdAt || 0),
                )
                .map((doc) => ({
                  ...doc,
                  id: String(doc.id),
                  name: doc.file_name,
                  createdAt: doc.created || doc.createdAt || "",
                  preview: doc.file_url,
                  file_type: doc.file_name
                    ? doc.file_name.split(".").pop().toLowerCase()
                    : "",
                }))}
              onRemove={handleRemoveDocumentFromTable}
              onAddDocument={handleAddDocument}
              isLoading={documentsLoading}
              showTableTitle={false}
            />
        </CenterBox>
      </Box>

      <Box width="20%" sx={{ flexShrink: 0, flexGrow: 0 }}>
        <Box
          width="100%"
          height="100%"
          sx={{ 
            backgroundColor: "background.box", 
            borderRadius: 2,
            minWidth: 0,
            maxWidth: "100%",
            overflow: "hidden"
          }}
        >
        </Box>
      </Box>
    </Box>
  );
}

export default RAGDocumentsPage;