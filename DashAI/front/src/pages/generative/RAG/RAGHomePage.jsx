import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Box } from "@mui/material";
import SelectOptionMenu from "../../../components/threeSectionLayout/SelectOptionMenu";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import SessionBar from "../../../components/generative/SessionBar";
import MainGenerativeBox from "../../../components/generative/MainGenerativeBox";
import DocumentsBar from "../../../components/generative/RAG/DocumentsBar";
import { getSessions, removeSession } from "../../../api/session";
import CenterBox from "../../../components/threeSectionLayout/panelContainers/CenterBox";

function RAGHomePage({
  onSessionCreated,
  onSessionSelect,
  sessions,
  setSessions,
  onNavigateToGenerative,
  isStandalone = false,
}) {
  const navigate = useNavigate();
  const [standaloneSessions, setStandaloneSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [documentRefreshTrigger, setDocumentRefreshTrigger] = useState(0);

  // Use sessions from props if available (embedded mode), otherwise manage own sessions (standalone mode)
  const currentSessions = sessions || standaloneSessions;
  const currentSetSessions = setSessions || setStandaloneSessions;

  const loadSessions = useCallback(async () => {
    if (isStandalone) {
      try {
        const allSessions = await getSessions();
        setStandaloneSessions(allSessions);
      } catch (error) {
        console.error("RAGHomePage: Error loading sessions:", error);
      }
    }
  }, [isStandalone]);

  useEffect(() => {
    if (isStandalone) {
      loadSessions();
    }
  }, [loadSessions, isStandalone]);

  const goToNextStep = (option) => {
    navigate(`/app/generative/rag/${option}`);
  };

  const handleNavigateToGenerative = () => {
    if (onNavigateToGenerative) {
      onNavigateToGenerative();
    } else {
      navigate("/app/generative");
    }
  };

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    if (isStandalone) {
      setSelectedSessionId(sessionId);
      // Navigate back to generative page with selected session
      navigate("/app/generative", { state: { selectedSessionId: sessionId } });
    } else if (onSessionSelect) {
      onSessionSelect(sessionId, taskName, taskDisplayName);
    }
  };

  const handleNewSessionButton = () => {
    if (isStandalone) {
      setSelectedSessionId(null);
    }
    // For embedded mode, this might be handled by parent
  };

  const handleSessionDelete = async (id) => {
    if (isStandalone) {
      setStandaloneSessions((prev) => prev.filter((s) => s.id !== id));
      await removeSession(id);
    }
    // For embedded mode, this might be handled by parent
  };

  const handleDocumentChange = () => {
    setDocumentRefreshTrigger((prev) => prev + 1);
  };

  if (isStandalone) {
    // Standalone layout with sidebar
    return (
      <Box height="calc(100vh - 74px)" width="100%" display="flex">
        <Box width="20%">
          <SessionBar
            sessions={currentSessions}
            selectedSessionId={selectedSessionId}
            handleSessionClick={handleSessionClick}
            handleNewSessionButton={handleNewSessionButton}
            handleSessionDelete={handleSessionDelete}
            stepIndex={0}
          />
        </Box>

        <Box width="60%">
          <CenterBox>
              <RAGBreadcrumbs />
              <SelectOptionMenu
                title="RAG Module"
                subtitle="Manage your Retrieval-Augmented Generation workflows: Create sessions, manage documents, and configure prompts for enhanced AI conversations."
                options={[
                  {
                    name: "sessions",
                    display_name: "Sessions",
                    description: "View existing RAG sessions and create new ones.",
                    Icon: null,
                  },
                  {
                    name: "prompts",
                    display_name: "Prompts",
                    description: "View existing prompts and create new ones.",
                    Icon: null,
                  },
                ]}
                searchBar={false}
                goToNextStep={goToNextStep}
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
            <DocumentsBar
              selectedSessionId={null}
              taskName="RAGTask"
              onDocumentChange={handleDocumentChange}
              key={`documents-standalone-${documentRefreshTrigger}`}
            />
          </Box>
        </Box>
      </Box>
    );
  }

  // Embedded layout (original)
  return (
    <Box
      display={"flex"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      gap={1}
      width={"100%"}
      height={"100%"}
      overflow={"scroll"}
      p={2}
    >
      <RAGBreadcrumbs 
        isEmbedded={true} 
        onNavigateToGenerative={handleNavigateToGenerative}
      />
      <SelectOptionMenu
        title="RAG Module"
        subtitle="Manage your Retrieval-Augmented Generation workflows: Create sessions, manage documents, and configure prompts for enhanced AI conversations."
        options={[
          {
            name: "sessions",
            display_name: "Sessions",
            description: "View existing RAG sessions and create new ones.",
            Icon: null,
          },
          {
            name: "documents",
            display_name: "Documents",
            description: "Detailed view and management of all documents.",
            Icon: null,
          },
          {
            name: "prompts",
            display_name: "Prompts",
            description: "View existing prompts and create new ones.",
            Icon: null,
          },
        ]}
        searchBar={false}
        goToNextStep={goToNextStep}
      />
    </Box>
  );
}

export default RAGHomePage;
