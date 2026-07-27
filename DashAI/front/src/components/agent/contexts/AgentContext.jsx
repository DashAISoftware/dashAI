import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useSnackbar } from "notistack";
import {
  fetchConversations,
  createConversation,
  updateConversationTitle,
  deleteConversation 
} from '../../../api/agent';

import { useTranslation } from "react-i18next";

const AgentContext = createContext(null);

export const useAgent = () => {
  return useContext(AgentContext);
};

export const AgentProvider = ({ children }) => {
  const { t } = useTranslation(["agent"]);
  const { enqueueSnackbar } = useSnackbar();
  const [conversations, setConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [loading, setLoading] = useState({ conversations: false});
  const [conversationTitle, setConversationTitle] = useState("");
  const [selectedConfigurationId, setSelectedConfigurationId] = useState(null);

  const loadConversations = useCallback(async () => {
    setLoading(prev => ({ ...prev, conversations: true }));
    try {
      const data = await fetchConversations();
      setConversations(data);
    } catch {
    } finally {
      setLoading(prev => ({ ...prev, conversations: false }));
    }
  }, []);

  const handleDeleteConversationById = useCallback(async (conversationId)=> {
    try {
    const response = await deleteConversation(conversationId);
      if (response.status === 204) {
        enqueueSnackbar(t("agent:message.deleteConversationSuccess"), {
          variant: "success",
        });
        setConversations(prev => prev.filter(c => c.id !== conversationId));
        setConversationTitle("");
        setSelectedConversationId(null);
      } else {
        enqueueSnackbar(t("agent:error.failedToDeleteConversation"), {
          variant: "error",
        });
      }
    } catch (error) {
      enqueueSnackbar(t("agent:error.failedToDeleteConversation"), {
        variant: "error",
      });
    }
  }, [t]);



  const handleCreateConversation = useCallback(async () => {
    const name = t("agent:prompt.newConversation");
    const newConv = await createConversation(name);
    setConversations(prev => [...prev, newConv]);
    setSelectedConversationId(newConv.id);
    setConversationTitle(name);
  }, [t]);

  const handleRenameConversation = useCallback(async (id, newTitle) => {
    try {
      await updateConversationTitle(id, newTitle);
      setConversations(prev =>
        prev.map(c => c.id === id ? { ...c, name: newTitle } : c)
      );
      setConversationTitle(newTitle);
      enqueueSnackbar(t("agent:message.updateTitleConversationSuccess"), {
        variant: "success",
      });
    } catch (error) {
      if (error.response?.status === 409) {
        enqueueSnackbar(t("agent:error.conversationNameExists"), {
          variant: "error",
        });
      } else if (error.response?.status === 422) {
        enqueueSnackbar(t("agent:error.conversationNameEmpty"), {
          variant: "error",
        });
      } else {
        enqueueSnackbar(t("agent:error.failedToUpdateConversationTitle"), {
          variant: "error",
        });
      }
      throw error;
    }
  }, [t]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
  if (selectedConversationId) {
    setConversationTitle(
      conversations.find(c => c.id === selectedConversationId)?.name || ""
    );
  }  
  }, [selectedConversationId]);


  const value = {
    conversations,
    selectedConversationId,
    setSelectedConversationId,
    loadConversations,
    handleCreateConversation,
    handleRenameConversation,
    handleDeleteConversationById,
    conversationTitle,
    selectedConfigurationId,
    setSelectedConfigurationId
  };

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
};








