import { useState, useEffect, useCallback } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";
import NewSessionModal from "./NewSessionModal/NewSessionModal";
import RAGSessionsTable from "./RAGSessionsTable";
import {
  getRAGSessions,
  createRAGSession,
  loadDocuments,
  deleteDocument,
} from "../../../api/rag";
import DocumentTable from "../../../components/generative/RAG/DocumentTable";
import PromptSelectionTable from "../../../components/generative/RAG/PromptSelectionTable";

function RAGHomePage({
  onSessionCreated,
  onSessionSelect,
  sessions,
  setSessions,
}) {
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editingSession, setEditingSession] = useState(null);
  const [allDocuments, setAllDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const data = await getRAGSessions();
      setSessions(data);
    } catch (error) {
      console.error("RAGHomePage: Error loading RAG sessions:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    try {
      const docs = await loadDocuments();
      setAllDocuments(docs);
    } catch (error) {
      console.error("RAGHomePage: Error loading all documents:", error);
    } finally {
      setDocumentsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
    fetchAllDocuments();
  }, [fetchAllDocuments, setSessions]);

  const handleOpenNewSessionModal = (session = null) => {
    setEditingSession(session);
    setShowModal(true);
  };

  const handleCreateOrUpdateSession = async (sessionData) => {
    try {
      const savedSession = await createRAGSession(sessionData);

      await loadSessions();
      setShowModal(false);

      return savedSession;
    } catch (error) {
      console.error("RAGHomePage: Error saving session:", error);
      throw error;
    }
  };

  const handleRemoveDocumentFromTable = useCallback(
    async (id) => {
      try {
        await deleteDocument(id);
        await fetchAllDocuments();
      } catch (error) {
        console.error("RAGHomePage: Failed to delete document:", error);
      }
    },
    [fetchAllDocuments],
  );

  const handleRemoveSession = useCallback(
    (id) => {
      setSessions((prev) => prev.filter((s) => s.id !== id));
    },
    [setSessions],
  );

  const handleAddDocument = useCallback((newDoc) => {
    setAllDocuments((prev) => [newDoc, ...prev]);
  }, []);

  return (
    <Box
      display={"flex"}
      width={"100%"}
      height={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"scroll"}
      paddingLeft={5}
      paddingRight={5}
      gap={1}
    >
      <Typography variant="h5" component="h1" sx={{ mt: 2 }}>
        RAG Sessions
      </Typography>
      <Typography variant="subtitle1" component="p" sx={{ mb: 1 }}>
        Manage your RAG sessions
      </Typography>
      <NewSessionModal
        open={showModal}
        onClose={() => {
          setShowModal(false);
          setEditingSession(null);
        }}
        onSessionSaved={handleCreateOrUpdateSession}
        onSessionSelect={onSessionSelect}
        session={editingSession}
        existingSessions={sessions}
      />

      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <RAGSessionsTable
          sessions={sessions.map((s) => ({ ...s, id: String(s.id) }))}
          onEdit={(session) => handleOpenNewSessionModal(session)}
          onSelect={onSessionSelect}
          onRefreshSessions={loadSessions}
          onOpenNewSessionModal={() => handleOpenNewSessionModal()}
          onRemove={handleRemoveSession}
          showTableTitle={true}
        />
      )}

      <Typography variant="h5" component="h2" sx={{ mt: 2 }}>
        Documents
      </Typography>
      <Typography variant="subtitle1" component="p" sx={{ mb: 2 }}>
        Manage documents for your RAG sessions
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
        showTableTitle={true}
      />

      <Typography variant="h5" component="h2" sx={{ mt: 2 }}>
        Prompts
      </Typography>
      <Typography variant="subtitle1" component="p" sx={{ mb: 2 }}>
        View all available prompts for your RAG sessions
      </Typography>
      <PromptSelectionTable
        showTableTitle={true}
        loading={false}
        rowSelectionModel={[]}
        onRowSelectionModelChange={() => {}}
      />
    </Box>
  );
}

export default RAGHomePage;
