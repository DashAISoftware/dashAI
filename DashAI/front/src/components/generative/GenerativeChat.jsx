import { Box, Divider, IconButton, Typography } from "@mui/material";
import React from "react";
import InfoIcon from "@mui/icons-material/Info";
import ArrowRightAltIcon from "@mui/icons-material/ArrowRightAlt";
import { ChatBubble } from "./ChatBubble";
import {
  getProcessById,
  getProcessesBySessionId,
  deleteProcessById,
} from "../../api/process";
import { useState, useEffect, useRef } from "react";
import { postProcess } from "../../api/process";
import { enqueueGenerativeProcessJob } from "../../api/job";
import { startJobQueue } from "../../api/job";
import { getHistoryBySessionId, getSessionById } from "../../api/session";
import InfoSessionModal from "./InfoSessionModal";
import HistoryIcon from "@mui/icons-material/History";
import ParameterHistoryModal from "./SessionHistoryModal";
import { useSnackbar } from "notistack";
import { TextInput } from "./TextInput";
import { MediaInput } from "./MediaInput";

export default function GenerativeChat({ sessionId, taskName, paramsVersion }) {
  const [history, setHistory] = useState([]);
  const [historyInfoVisible, setHistoryInfoVisible] = useState(false);
  const [messages, setMessages] = useState([]);
  const [messagesWithHistory, setMessagesWithHistory] = useState([]);
  const [isLoadingMessage, setIsLoadingMessage] = useState(false);
  const chatContainerRef = useRef(null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [sessionInfoVisible, setSessionInfoVisible] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  };

  const getSessionInfo = () => {
    getSessionById(sessionId).then((response) => {
      setSessionInfo(response);
    });
  };

  const getMessages = () => {
    getProcessesBySessionId(sessionId).then((response) => {
      setIsLoadingMessage(false);
      setMessages(response);
    });
  };

  const getHistory = () => {
    getHistoryBySessionId(sessionId).then((response) => {
      setHistory(response);
    });
  };

  const handleSendMessage = (input) => {
    // Set the Loading state to true
    setIsLoadingMessage(true);

    // Send the message to the server
    postProcess(sessionId, input).then((response) => {
      // Update the messages state with the new message
      // and reset the input field
      setMessages((prevMessages) => [...prevMessages, response]);
      // Wait 1/2 second before enqueing the job to get the input properly from the server
      setTimeout(() => {
        // Enqueue the job
        enqueueGenerativeProcessJob(response.id).then(() => {
          // Start the job queue
          startJobQueue(true).then(() => {
            // Set a timeout to refresh the messages
            setTimeout(() => {
              // Refresh the messages after 1 seconds
              getProcessById(response.id).then((response) => {
                // Check if the process is finished
                if (response.status === 4) {
                  setIsLoadingMessage(false);
                  enqueueSnackbar("The process has failed. Deleting it...");

                  deleteProcessById(response.id).then(() => {
                    setMessages((prevMessages) =>
                      prevMessages.filter(
                        (message) => message.id !== response.id,
                      ),
                    );
                  });
                } else {
                  setIsLoadingMessage(false);
                  setMessages((prevMessages) => {
                    const updatedMessages = prevMessages.map((message) =>
                      message.id === response.id ? response : message,
                    );
                    return updatedMessages;
                  });
                }
              });
            }, 1000);
          });
        });
      }, 500);
    });
  };

  useEffect(() => {
    getMessages();
    getSessionInfo();
    getHistory();
  }, [sessionId, paramsVersion]);

  useEffect(() => {
    setMessages([]);
  }, [taskName]);

  useEffect(() => {
    scrollToBottom();
  }, [messagesWithHistory]);

  useEffect(() => {
    let messagesObject = messages.map((process) => {
      return {
        type: "message",
        timestamp: process.created,
        id: process.id,
        input: process.input,
        output: process.output,
        status: process.status,
        end_time: process.end_time,
      };
    });

    let historyObject = history.map((entry) => {
      return {
        type: "history",
        timestamp: entry.timestamp,
        id: entry.id,
        changedMessage: entry.changes.map((change) => (
          <span
            key={change.parameter}
            style={{
              display: "inline-flex",
              alignItems: "center",
              whiteSpace: "pre-wrap",
            }}
          >
            {change.parameter}: {change.oldValue}{" "}
            <ArrowRightAltIcon fontSize="small" /> {change.newValue}{" "}
          </span>
        )),
      };
    });

    let combinedMessages = [...messagesObject, ...historyObject];
    combinedMessages.sort(
      (a, b) => new Date(a.timestamp) - new Date(b.timestamp),
    );
    setMessagesWithHistory(combinedMessages);
  }, [messages, history]);

  return (
    <Box
      display="flex"
      flexDirection="column"
      justifyContent="flex-start"
      alignItems="center"
      gap={1}
      width={"100%"}
      height={"100%"}
    >
      {/* Model display */}
      <Box
        sx={{
          width: "100%",
          height: "30px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          alignItems: "center",
          borderRadius: 1,
          opacity: 0.5,
          mb: 1,
        }}
      >
        <Box
          display="flex"
          flexDirection="row"
          alignItems="center"
          justifyContent="space-between"
          gap={0.5}
          width={"100%"}
        >
          <Typography>
            {sessionInfo?.id} - {sessionInfo?.name}{" "}
            {sessionInfo?.description ? ":" : null} {sessionInfo?.description}
          </Typography>

          <Box>
            <IconButton onClick={() => setHistoryInfoVisible(true)}>
              <HistoryIcon
                sx={{
                  color: "#a0a0a0",
                  "&:hover": {
                    color: "#ffffff",
                  },
                }}
              />
            </IconButton>

            <IconButton onClick={() => setSessionInfoVisible(true)}>
              <InfoIcon
                sx={{
                  color: "#a0a0a0",
                  "&:hover": {
                    color: "#ffffff",
                  },
                }}
              />
            </IconButton>
          </Box>
        </Box>
      </Box>

      <Divider sx={{ width: "100%" }} />

      {/* Chat display */}
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="flex-start"
        alignItems="flex-start"
        gap={1}
        width={"100%"}
        height={"100%"}
        overflow={"auto"}
        mt={1}
        p={2}
        ref={chatContainerRef}
        sx={{
          "&::-webkit-scrollbar": {
            width: "8px",
          },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: "#555",
            borderRadius: "4px",
          },
          "&::-webkit-scrollbar-thumb:hover": {
            backgroundColor: "#888",
          },
        }}
      >
        {messagesWithHistory?.map((message) => {
          return (
            <Box
              key={`${message.type}_${message.id}`}
              display="flex"
              flexDirection="column"
              justifyContent="flex-start"
              flexGrow={0}
              gap={1}
              width={"100%"}
              //height={"100%"}
              mt={1}
            >
              {message.type === "history" ? (
                <Typography sx={{ fontSize: "0.875rem", opacity: 0.8 }}>
                  Params updated: {message.changedMessage}
                </Typography>
              ) : (
                <>
                  <ChatBubble
                    messages={message.input}
                    sender={"User"}
                    timestamp={new Date(message.timestamp).toLocaleTimeString()}
                    isUser={true}
                  />
                  {message.status === 3 ? (
                    <ChatBubble
                      messages={message.output}
                      sender={"Model"}
                      timestamp={new Date(
                        message.end_time,
                      ).toLocaleTimeString()}
                    />
                  ) : (
                    <ChatBubble isWaiting={true} sender="Model" />
                  )}
                </>
              )}
            </Box>
          );
        })}
      </Box>

      {/* Chat input */}
      {taskName === "ControlNetTask" ? (
        <MediaInput
          onSendMessage={(input) => {
            handleSendMessage(input);
          }}
          isLoading={isLoadingMessage}
        />
      ) : (
        <TextInput
          onSendMessage={(input) => {
            handleSendMessage(input);
          }}
          isLoading={isLoadingMessage}
        />
      )}

      {/* Session Info Modal */}
      {sessionInfo && (
        <InfoSessionModal
          sessionData={sessionInfo}
          open={sessionInfoVisible}
          onClose={() => setSessionInfoVisible(false)}
        />
      )}

      {/* Parameter History Modal */}
      <ParameterHistoryModal
        historyChanges={history}
        open={historyInfoVisible}
        taskName={taskName}
        setOpen={setHistoryInfoVisible}
      />
    </Box>
  );
}
