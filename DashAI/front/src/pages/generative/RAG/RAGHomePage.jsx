import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box } from "@mui/material";
import SelectOptionMenu from "../../../components/threeSectionLayout/SelectOptionMenu";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";

function RAGHomePage({
  onSessionCreated,
  onSessionSelect,
  sessions,
  setSessions,
  onNavigateToGenerative,
}) {
  const navigate = useNavigate();

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
  );
}

export default RAGHomePage;
