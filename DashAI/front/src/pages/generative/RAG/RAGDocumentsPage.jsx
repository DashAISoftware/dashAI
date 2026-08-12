import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Typography } from "@mui/material";
import ModuleContainer from "../../../components/layout/ModuleContainer";
import LeftPanel from "../../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../../components/generative/SessionBar";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import DocumentTable from "../../../components/generative/RAG/DocumentTable";
import DocumentDetailPanel from "../../../components/generative/RAG/DocumentDetailPanel";
import { loadDocuments, deleteDocument } from "../../../api/rag";
import { getSessions, removeSession } from "../../../api/session";
import { useThreePanelLayout } from "../../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { FormSchemaProvider } from "../../../contexts/schema";

/**
 * RAG documents management page.
 * Shows a document table in the center, sessions in the left panel,
 * and allows document upload / deletion.
 * @returns {JSX.Element} Three-panel documents page.
 */
function RAGDocumentsPage() {
  const navigate = useNavigate();
  const threePanelLayout = useThreePanelLayout();
  const { t } = useTranslation(["generative"]);
  const [allDocuments, setAllDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);

  /**
   * Fetch all sessions from the API.
   */
  const loadSessions = useCallback(async () => {
    try {
      const allSessions = await getSessions();
      setSessions(allSessions);
    } catch (error) {
      console.error("RAGDocumentsPage: Error loading sessions:", error);
    }
  }, []);

  /**
   * Load all RAG documents from the API.
   */
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

  /**
   * Delete a document via the API and refresh the list.
   * @param {number} id - Document id to delete.
   */
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

  /**
   * Prepend a newly uploaded document to the local list.
   * @param {object} newDoc - The document returned by the upload API.
   */
  const handleAddDocument = useCallback((newDoc) => {
    setAllDocuments((prev) => [newDoc, ...prev]);
  }, []);

  /**
   * Navigate to the main generative page with the selected session pre-selected.
   * @param {number} sessionId
   * @param {string} taskName
   * @param {string} taskDisplayName
   */
  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    navigate("/app/generative", {
      state: {
        selectedSessionId: sessionId,
        selectedTaskName: taskName,
        selectedDisplayName: taskDisplayName,
      },
    });
  };

  const handleNewSessionButton = () => {
    navigate("/app/generative");
  };

  /**
   * Remove a session optimistically and persist the deletion.
   * @param {number} id - Session id to delete.
   */
  const handleSessionDelete = async (id) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    await removeSession(id);
  };

  return (
    <FormSchemaProvider>
      <ThreePanelLayoutContext.Provider value={threePanelLayout}>
        <ModuleContainer>
          <LeftPanel data-tour="sessions-left-panel">
            <SessionBar
              sessions={sessions}
              handleSessionClick={handleSessionClick}
              handleNewSessionButton={handleNewSessionButton}
              handleSessionDelete={handleSessionDelete}
              stepIndex={0}
              onToggle={threePanelLayout.handleToggleLeft}
              showSearch={false}
            />
          </LeftPanel>

          <CenterPanel data-tour="documents-center-panel">
            <RAGBreadcrumbs />
            <Typography variant="h5" component="h1">
              {t("generative:ragDocumentsPage.title")}
            </Typography>
            <Typography variant="subtitle1" component="p" sx={{ mb: 2 }}>
              {t("generative:ragDocumentsPage.description")}
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
                  preview: doc.preview_url,
                  file_type: doc.file_name
                    ? doc.file_name.split(".").pop().toLowerCase()
                    : "",
                }))}
              onRemove={handleRemoveDocumentFromTable}
              onAddDocument={handleAddDocument}
              onSelectDocument={setSelectedDocument}
              isLoading={documentsLoading}
              showTableTitle={false}
            />
          </CenterPanel>

          <RightPanel toggleButtonTop="50%" data-tour="documents-right-panel">
            <DocumentDetailPanel
              selectedDocument={selectedDocument}
              onExtractorChanged={fetchAllDocuments}
            />
          </RightPanel>
        </ModuleContainer>
      </ThreePanelLayoutContext.Provider>
    </FormSchemaProvider>
  );
}

export default RAGDocumentsPage;
