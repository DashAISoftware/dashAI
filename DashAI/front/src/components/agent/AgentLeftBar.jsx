import { useState, useMemo } from "react";
import { Box, Divider, Typography } from "@mui/material";
import ChatIcon from "@mui/icons-material/Chat";
import Footer from "../threeSectionLayout/Footer";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import { useTranslation } from "react-i18next";
import { useAgent } from "./contexts/AgentContext";

export default function AgentLeftBar() {
  const { t } = useTranslation(["agent"]);
  const {
    conversations,
    selectedConversationId,
    setSelectedConversationId,
    handleDeleteConversationById,
    handleCreateConversation,
    handleRenameConversation,
  } = useAgent();

  const [searchQuery, setSearchQuery] = useState("");

  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const lowerQuery = searchQuery.toLowerCase();
    return conversations.filter((conv) =>
      (conv.name || "").toLowerCase().includes(lowerQuery),
    );
  }, [conversations, searchQuery]);

  const getDeleteConfirmationContent = (conversation) =>
    t("agent:label.confirmDeleteConversation", {
      name: conversation.name,
    });

  return (
    <SideBar>
      <Box
        p={2}
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: 1,
        }}
      >
        <NewItemButton
          onClick={handleCreateConversation}
          title={t("agent:button.newConversation")}
        />
        <Typography variant="body1" color="textSecondary">
          {t("agent:label.conversationsModule")}
        </Typography>
      </Box>

      <Box px={2} pb={2} flex="0 0 auto">
        <SearchBar
          placeholder={t("agent:label.searchConversations")}
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
        />
      </Box>

      <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

      <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
        <CollapsibleList
          items={filteredConversations}
          selectedItemId={selectedConversationId}
          onItemClick={setSelectedConversationId}
          onItemDelete={handleDeleteConversationById}
          onItemEdit={handleRenameConversation}
          title={t("agent:label.conversations")}
          Icon={ChatIcon}
          defaultOpen={true}
          getDeleteConfirmationContent={getDeleteConfirmationContent}
        />

      </Box>


      <Footer />
    </SideBar>
  );
}
