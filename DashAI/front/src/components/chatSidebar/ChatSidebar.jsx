import { Box, CircularProgress, IconButton, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";
import CloseIcon from "@mui/icons-material/Close";
import { ChatBubble } from "../generative/ChatBubble";
import {
  deleteProcessById,
  fetchMessages,
  getProcessById,
  enqueueAgenticProcessJob,
  postProcess,
} from "../../api/agent";
import { useState, useEffect, useRef, useCallback } from "react";
import { MediaInput } from "../agent/MediaInput";
import { useChatSidebar } from "./ChatSidebarContext";

const MIN_WIDTH = 340;
const MAX_WIDTH = 700;
const DEFAULT_WIDTH = 380;
const RESIZE_HANDLE_WIDTH = 6;

export default function ChatSidebar() {
  const theme = useTheme();
  const { t } = useTranslation();

  const {
    sidebarOpen,
    selectedConfigurationId,
    selectedConversationId,
    configurations,
    conversations,
    closeSidebar,
    setSidebarWidth,
  } = useChatSidebar();

  const selectedConversation = conversations.find(
    (conversation) => `${conversation.id}` === `${selectedConversationId}`,
  );

  const [messages, setMessages] = useState([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isLoadingMessage, setIsLoadingMessage] = useState(false);
  const chatContainerRef = useRef(null);
  const shouldScrollToBottomRef = useRef(false);

  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  };

  const getMessages = async () => {
    if (!selectedConversationId) {
      setMessages([]);
      return;
    }

    setIsLoadingMessages(true);
    try {
      const data = await fetchMessages(selectedConversationId);
      setMessages(data);
      shouldScrollToBottomRef.current = true;
    } catch (error) {
      console.error("ChatSidebar: failed to fetch messages", error);
    } finally {
      setIsLoadingMessages(false);
    }
  };

  const handleSendMessage = async (input) => {
    if (!selectedConversationId) return;
    if (!selectedConfigurationId) {
      console.warn("ChatSidebar: configuration is required to send messages");
      return;
    }

    setIsLoadingMessage(true);
    try {
      const response = await postProcess(
        selectedConversationId,
        selectedConfigurationId,
        input,
      );
      setMessages((prevMessages) => [...prevMessages, response]);
      shouldScrollToBottomRef.current = true;
      await enqueueAgenticProcessJob(response.id, selectedConfigurationId);
    } catch (error) {
      console.error("ChatSidebar: failed to send message", error);
    } finally {
      setIsLoadingMessage(false);
    }
  };

  useEffect(() => {
    getMessages();
  }, [sidebarOpen]);

  useEffect(() => {
    if (shouldScrollToBottomRef.current) {
      scrollToBottom();
      shouldScrollToBottomRef.current = false;
    }
  }, [messages]);

  useEffect(() => {
    if (messages.length === 0) return;

    const POLL_INTERVAL = 1500;

    const intervalId = setInterval(() => {
      const unfinished = messages.filter(
        (m) => m.status !== 3 && m.status !== 4,
      );

      if (unfinished.length === 0) {
        clearInterval(intervalId);
        return;
      }

      unfinished.forEach((msg) => {
        getProcessById(msg.id)
          .then((process) => {
            const status = process.status;

            if (status === 4) {
              deleteProcessById(process.id).then(() => {
                setMessages((prev) => prev.filter((m) => m.id !== process.id));
              });
            } else {
              setMessages((prev) =>
                prev.map((m) => (m.id === process.id ? process : m)),
              );
              window.dispatchEvent(new CustomEvent("dashai-refresh"));
            }
          })
          .catch((error) => {
            console.error("ChatSidebar: polling failed", error);
          });
      });
    }, POLL_INTERVAL);
    return () => clearInterval(intervalId);
  }, [messages]);

  useEffect(() => {
    if (sidebarOpen) {
      setSidebarWidth(width);
    }
  }, [sidebarOpen, width, setSidebarWidth]);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e) => {
      const newWidth = window.innerWidth - e.clientX;
      setWidth(Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, newWidth)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing]);

  if (!sidebarOpen || !selectedConversationId) {
    return null;
  }

  return (
    <Box
      sx={{
        position: "fixed",
        top: "74px",
        right: 0,
        bottom: 0,
        width: `${width}px`,
        zIndex: 1100,
        display: "flex",
        flexDirection: "row",
        boxShadow: "-4px 0 12px rgba(0,0,0,0.15)",
        transition: isResizing ? "none" : "width 0.1s ease",
      }}
    >
      <Box
        onMouseDown={handleMouseDown}
        sx={{
          width: `${RESIZE_HANDLE_WIDTH}px`,
          cursor: "col-resize",
          flexShrink: 0,
          backgroundColor: isResizing
            ? theme.palette.primary.main
            : "transparent",
          "&:hover": {
            backgroundColor: theme.palette.primary.light,
            opacity: 0.5,
          },
          transition: "background-color 0.15s",
        }}
      />

      <Box
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          backgroundColor: theme.palette.background.paper,
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 2,
            py: 1.2,
            borderBottom: `1px solid ${theme.palette.divider}`,
            flexShrink: 0,
          }}
        >
          <Typography
            variant="subtitle1"
            fontWeight="bold"
            noWrap
            sx={{ flex: 1 }}
          >
            {selectedConversation?.name}
          </Typography>
          <IconButton size="small" onClick={closeSidebar}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>

        <Box
          ref={chatContainerRef}
          sx={{
            flex: 1,
            overflowY: "auto",
            p: 2,
            display: "flex",
            flexDirection: "column",
            gap: 1,
            "&::-webkit-scrollbar": {
              width: "8px",
            },
            "&::-webkit-scrollbar-thumb": {
              backgroundColor:
                theme.palette.ui?.border || theme.palette.divider,
              borderRadius: "4px",
            },
            "&::-webkit-scrollbar-thumb:hover": {
              backgroundColor:
                theme.palette.ui?.hover || theme.palette.action.hover,
            },
          }}
        >
          {isLoadingMessages ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
              }}
            >
              <CircularProgress size={24} />
            </Box>
          ) : messages.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                opacity: 0.5,
              }}
            >
              <Typography variant="body2" color="text.secondary">
                {t("chatsidebar:emptyConversation")}
              </Typography>
            </Box>
          ) : (
            messages.map((message) => {
              const inputMessage = message.input?.find((msg) => msg.is_input);
              const outputMessage = message.output?.find(
                (msg) => !msg.is_input,
              );

              return (
                <Box
                  key={message.id}
                  display="flex"
                  flexDirection="column"
                  justifyContent="flex-start"
                  flexGrow={0}
                  gap={1}
                  width={"100%"}
                  mt={1}
                >
                  {!!inputMessage?.text && (
                    <ChatBubble
                      messages={[
                        {
                          id: inputMessage.id,
                          data_type: "str",
                          data: inputMessage.text,
                        },
                      ]}
                      sender={"User"}
                      timestamp={new Date(
                        message.start_time,
                      ).toLocaleTimeString()}
                      isUser={true}
                    />
                  )}
                  {!!outputMessage?.text ? (
                    <ChatBubble
                      messages={[
                        {
                          id: outputMessage.id,
                          data_type: "str",
                          data: outputMessage.text,
                        },
                      ]}
                      sender={"Agent"}
                      timestamp={new Date(
                        message.end_time,
                      ).toLocaleTimeString()}
                    />
                  ) : (
                    <ChatBubble isWaiting={true} sender="Agent" />
                  )}
                </Box>
              );
            })
          )}
        </Box>

        <Box
          sx={{
            px: 2,
            py: 1.5,
            borderTop: `1px solid ${theme.palette.divider}`,
            flexShrink: 0,
          }}
        >
          <MediaInput
            key={selectedConversationId}
            onSendMessage={handleSendMessage}
            isLoading={isLoadingMessage}
          />
        </Box>
      </Box>
    </Box>
  );
}
