import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Box } from "@mui/material";
import ModuleContainer from "../../../components/layout/ModuleContainer";
import LeftPanel from "../../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../../components/threeSectionLayout/panels/RightPanel";
import SelectOptionMenu from "../../../components/threeSectionLayout/SelectOptionMenu";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import SessionBar from "../../../components/generative/SessionBar";
import DocumentsBar from "../../../components/generative/RAG/DocumentsBar";
import GenerativeChat from "../../../components/generative/GenerativeChat";
import RAGSessionSummary from "../../../components/generative/RAG/RAGSessionSummary";
import { removeSession } from "../../../api/session";
import { useGenerative } from "../../../components/generative/GenerativeContext";
import { useThreePanelLayout } from "../../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../../components/threeSectionLayout/panels/ThreePanelLayoutContext";

const ragOptions = [
  {
    name: "sessions",
    display_name: "RAG Sessions",
    description: "View existing RAG sessions and create new ones.",
    Icon: null,
  },
  {
    name: "documents",
    display_name: "RAG Documents",
    description: "Manage the documents used by RAG sessions.",
    Icon: null,
  },
  {
    name: "prompts",
    display_name: "RAG Prompts",
    description: "View existing prompts and create new ones.",
    Icon: null,
  },
];

function RAGHomePage({ onSessionSelect, sessions, setSessions }) {
  const navigate = useNavigate();
  const threePanelLayout = useThreePanelLayout();
  const generative = useGenerative() ?? {};
  const [showRagChat, setShowRagChat] = useState(false);

  const {
    sessions: contextSessions,
    setSessions: setContextSessions,
    selectedSessionId: globalSelectedSessionId,
    setSelectedSessionId: setGlobalSelectedSessionId,
    selectedTaskName,
    setSelectedTaskName,
    setSelectedDisplayName,
    setStepIndex,
  } = generative;

  const currentSessions = sessions || contextSessions || [];
  const currentSetSessions = setSessions || setContextSessions;
  const isRagSessionSelected =
    selectedTaskName === "RAGTask" && Boolean(globalSelectedSessionId);

  useEffect(() => {
    if (!isRagSessionSelected) {
      setShowRagChat(false);
    }
  }, [isRagSessionSelected, globalSelectedSessionId]);

  const handleStartRagChat = () => {
    setShowRagChat(true);
  };

  const goToNextStep = (option) => {
    navigate(`/app/generative/RAG/${option}`);
  };

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    if (onSessionSelect) {
      onSessionSelect(sessionId, taskName, taskDisplayName);
      return;
    }

    setGlobalSelectedSessionId?.(sessionId);
    setSelectedTaskName?.(taskName);
    setSelectedDisplayName?.(taskDisplayName);
    setStepIndex?.(0);

    if (taskName !== "RAGTask") {
      navigate("/app/generative", {
        replace: true,
        state: {
          selectedSessionId: sessionId,
          taskName,
          taskDisplayName,
          fromSessionSelection: true,
        },
      });
    }
  };

  const handleNewSessionButton = () => {
    setGlobalSelectedSessionId?.(null);
    setSelectedTaskName?.("RAGTask");
    setSelectedDisplayName?.(null);
    setStepIndex?.(0);
  };

  const handleSessionDelete = async (id) => {
    currentSetSessions?.((prev) => prev.filter((s) => s.id !== id));
    if (id === globalSelectedSessionId) {
      setGlobalSelectedSessionId?.(null);
    }
    await removeSession(id);
  };

  const ragContent = (
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
      <RAGBreadcrumbs />
      <SelectOptionMenu
        title="RAG Module"
        subtitle="Manage your Retrieval-Augmented Generation workflows: Create sessions, manage documents, and configure prompts for enhanced AI conversations."
        options={ragOptions}
        searchBar={false}
        goToNextStep={goToNextStep}
      />
    </Box>
  );

  const centerContent = isRagSessionSelected ? (
    showRagChat ? (
      <GenerativeChat />
    ) : (
      <RAGSessionSummary
        sessionId={globalSelectedSessionId}
        onStartChat={handleStartRagChat}
      />
    )
  ) : (
    ragContent
  );

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel data-tour="sessions-left-panel">
          <SessionBar
            sessions={currentSessions}
            selectedSessionId={globalSelectedSessionId}
            handleSessionClick={handleSessionClick}
            handleNewSessionButton={handleNewSessionButton}
            handleSessionDelete={handleSessionDelete}
            stepIndex={0}
            onToggle={threePanelLayout.handleToggleLeft}
          />
        </LeftPanel>

        <CenterPanel data-tour="task-gallery">
          {centerContent}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%" data-tour="parameters-right-panel">
          <Box
            width="100%"
            height="100%"
            sx={{
              backgroundColor: "background.box",
              borderRadius: 2,
              minWidth: 0,
              maxWidth: "100%",
              overflow: "hidden",
            }}
          >
            <DocumentsBar
              selectedSessionId={isRagSessionSelected ? globalSelectedSessionId : null}
              taskName="RAGTask"
              key={`rag-docs-${isRagSessionSelected ? globalSelectedSessionId : "all"}`}
            />
          </Box>
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}

export default RAGHomePage;
