import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Box } from "@mui/material";
import SessionBar from "../../../components/generative/SessionBar";
import MainGenerativeBox from "../../../components/generative/MainGenerativeBox";
import SelectOptionMenu from "../../../components/threeSectionLayout/SelectOptionMenu";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import { getSessions, removeSession } from "../../../api/session";

function RAGStandaloneHomePage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);

  const loadSessions = useCallback(async () => {
    try {
      const allSessions = await getSessions();
      setSessions(allSessions);
    } catch (error) {
      console.error("RAGStandaloneHomePage: Error loading sessions:", error);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const goToNextStep = (option) => {
    navigate(`/app/generative/rag/${option}`);
  };

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    setSelectedSessionId(sessionId);
    // Navigate back to generative page with selected session
    navigate("/app/generative", { state: { selectedSessionId: sessionId } });
  };

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
  };

  const handleSessionDelete = async (id) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    await removeSession(id);
  };

  return (
    <Box height="calc(100vh - 74px)" width="100%" p={1.5} pb={1} display="flex">
      <Box width="22%" mr={1}>
        <SessionBar
          sessions={sessions}
          selectedSessionId={selectedSessionId}
          handleSessionClick={handleSessionClick}
          handleNewSessionButton={handleNewSessionButton}
          handleSessionDelete={handleSessionDelete}
          stepIndex={0}
        />
      </Box>

      <Box width="56%" mr={1}>
        <MainGenerativeBox>
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
              subtitle="Manage your Retrieval-Augmented Generation workflows: Create sessions, upload documents, and configure prompts for enhanced AI conversations."
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
                  description: "View existing documents and upload new ones.",
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
        </MainGenerativeBox>
      </Box>

      <Box width="22%">
        <Box
          width="100%"
          height="100%"
          sx={{ backgroundColor: "background.box", borderRadius: 2 }}
        >
        </Box>
      </Box>
    </Box>
  );
}

export default RAGStandaloneHomePage;