import React, { useState, useEffect } from 'react';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import CustomLayout from '../../../components/custom/CustomLayout';
import NewSessionModal from './NewSessionModal';
import RAGSessionsTable from './RAGSessionsTable';
import { getRAGSessions, createRAGSession } from '../../../api/rag';

function RAGHomePage({ onSessionCreated, onSessionSelect }) {
  const [showModal, setShowModal] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingSession, setEditingSession] = useState(null);

  const loadSessions = async () => {
    setLoading(true); // Set loading to true when fetching
    try {
      const data = await getRAGSessions();
      setSessions(data);
      console.log("RAGHomePage: Sessions loaded:", data);
    } catch (error) {
      console.error("RAGHomePage: Error loading RAG sessions:", error);
    } finally {
      setLoading(false); // Set loading to false after fetch
      console.log("RAGHomePage: Loading finished.");
    }
  };

  // Cargar sesiones al iniciar
  useEffect(() => {
    console.log("RAGHomePage: useEffect - Initial session load...");
    loadSessions();
  }, []); // Empty dependency array means this runs once on mount

  const handleOpenNewSessionModal = (session = null) => {
    console.log("RAGHomePage: handleOpenNewSessionModal called.");
    setEditingSession(session); // Set the session to edit
    setShowModal(true); // Open the modal
    console.log("RAGHomePage: showModal set to true.");
  };

  const handleCreateOrUpdateSession = async (sessionData) => {
    console.log("RAGHomePage: handleCreateOrUpdateSession called with data:", sessionData);
    try {
      const savedSession = await createRAGSession(sessionData);
      console.log("RAGHomePage: New/Updated RAG session saved:", savedSession);

      // Refresh the sessions list after creation/update
      await loadSessions(); // Call loadSessions to get the latest data

      onSessionCreated(savedSession); // Notify parent component (Generative.jsx)
      setShowModal(false); // Close the modal
      console.log("RAGHomePage: Modal closed after session save.");
      return savedSession;
    } catch (error) {
      console.error("RAGHomePage: Error creating/updating session:", error);
      throw error; // Re-throw to handle in the modal if needed
    }
  };

  console.log("RAGHomePage: Render. Current showModal state:", showModal);

  return (
    <CustomLayout
      title="RAG Sessions"
      subtitle="Manage your RAG sessions"
      actionButton={
        <Button
          variant="contained"
          color="primary"
          onClick={() => handleOpenNewSessionModal()}
          sx={{ textTransform: 'none' }}
        >
          New Session
        </Button>
      }
    >
      {/* Modal para nueva sesión */}
      <NewSessionModal
        open={showModal}
        onClose={() => {
          setShowModal(false);
          setEditingSession(null); // Clear editing session when closing
          console.log("RAGHomePage: Modal onClose called. showModal set to false.");
        }}
        onSessionSaved={handleCreateOrUpdateSession}
        onSessionSelect={onSessionSelect}
        session={editingSession}
      />

      {/* Contenido principal */}
      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <RAGSessionsTable
          sessions={sessions}
          onEdit={(session) => handleOpenNewSessionModal(session)}
          onSelect={onSessionSelect}
          onRefreshSessions={loadSessions} // Pass the refresh function
          onOpenNewSessionModal={() => handleOpenNewSessionModal()} // Pass function to open modal
        />
      )}
    </CustomLayout>
  );
}

export default RAGHomePage;