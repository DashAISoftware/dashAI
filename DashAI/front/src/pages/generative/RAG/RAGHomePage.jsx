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

  useEffect(() => {
    loadSessions();
  }, []); 

  const handleOpenNewSessionModal = (session = null) => {
    setEditingSession(session);
    setShowModal(true); 
  };

  const handleCreateOrUpdateSession = async (sessionData) => {
    try {
      const savedSession = await createRAGSession(sessionData);
      console.log("RAGHomePage: New/Updated RAG session saved:", savedSession);

      await loadSessions();
      onSessionCreated(savedSession);
      setShowModal(false); 
      
      return savedSession;

    } catch (error) {
      throw error;
    }
  };

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
      <NewSessionModal
        open={showModal}
        onClose={() => {
          setShowModal(false);
          setEditingSession(null);
        }}
        onSessionSaved={handleCreateOrUpdateSession}
        onSessionSelect={onSessionSelect}
        session={editingSession}
      />

      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <RAGSessionsTable
          sessions={sessions}
          onEdit={(session) => handleOpenNewSessionModal(session)}
          onSelect={onSessionSelect}
          onRefreshSessions={loadSessions} 
          onOpenNewSessionModal={() => handleOpenNewSessionModal()}
        />
      )}
    </CustomLayout>
  );
}

export default RAGHomePage;