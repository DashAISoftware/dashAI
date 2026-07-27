import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import {
  fetchAgentConfigurations,
  fetchConversations as fetchAgentConversations,
} from "../../api/agent";

const ChatSidebarContext = createContext(null);

export const useChatSidebar = () => useContext(ChatSidebarContext);

export function ChatSidebarProvider({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(0);
  const [selectedConfigurationId, setSelectedConfigurationId] = useState(null);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [configurations, setConfigurations] = useState([]);
  const [conversations, setConversations] = useState([]);

  const fetchConfigurations = useCallback(async () => {
    const data = await fetchAgentConfigurations();
    setConfigurations(data);

  }, []);

  const fetchConversations = useCallback(async () => {

    const data = await fetchAgentConversations();
    setConversations(data);

  }, []);


  const openSidebar = useCallback((configurationId, conversationId) => {
    setSelectedConfigurationId(configurationId);
    setSelectedConversationId(conversationId);
    setSidebarOpen(true);
  }, []);

  const selectConfiguration = useCallback((configurationId) => {
    setSelectedConfigurationId(configurationId);
    setSelectedConversationId(null);
  }, []);

  const selectConversation = useCallback((conversationId) => {
    setSelectedConversationId(conversationId);
  }, []);

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false);
    setSidebarWidth(0);
  }, []);

  const value = {
    sidebarOpen,
    sidebarWidth,
    setSidebarWidth,
    configurations,
    conversations,
    selectedConfigurationId,
    selectedConversationId,
    setSelectedConfigurationId,
    setSelectedConversationId,
    selectConfiguration,
    selectConversation,
    openSidebar,
    closeSidebar,
    fetchConfigurations,
    fetchConversations
  };

  return (
    <ChatSidebarContext.Provider value={value}>
      {children}
    </ChatSidebarContext.Provider>
  );
}
