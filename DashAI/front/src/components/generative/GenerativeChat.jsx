import { Box, Divider, IconButton, Typography, Button } from "@mui/material";
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
import { useSnackbar } from "notistack";
import { TextInput } from "./TextInput";
import { MediaInput } from "./MediaInput";
import JobQueueWidget from "../jobs/JobQueueWidget";
import { getRunStatus } from "../../utils/runStatus";
import TemplateModal from "../custom/TemplateModal";

export default function GenerativeChat({ sessionId, taskName, paramsVersion }) {
  const [history, setHistory] = useState([]);
  const [messages, setMessages] = useState([]);
  const [messagesWithHistory, setMessagesWithHistory] = useState([]);
  const [isLoadingMessage, setIsLoadingMessage] = useState(false);
  const chatContainerRef = useRef(null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [sessionInfoVisible, setSessionInfoVisible] = useState(false);
  const [referenceModalOpen, setReferenceModalOpen] = useState(false);
  const [selectedReferenceText, setSelectedReferenceText] = useState("");
  const [referenceModalTitle, setReferenceModalTitle] = useState("");
  const { enqueueSnackbar } = useSnackbar();

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  };

  const handleOpenReference = (ref, key) => {
    const title = `Document ${ref.document_id}${ref.document_position ? ` - Chunk ${ref.document_position}` : ''}`;
    setReferenceModalTitle(title);
    // Convert escaped newlines to actual newlines
    setSelectedReferenceText(ref.text.replace(/\\n/g, '\n'));
    setReferenceModalOpen(true);
  };

  const getSessionInfo = () => {
    getSessionById(sessionId).then((response) => {
      setSessionInfo(response);
    });
  };

  const getMessages = () => {
    getProcessesBySessionId(sessionId).then((response) => {
      console.log('Fetched messages:', response); // Add here
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
    setIsLoadingMessage(true);

    postProcess(sessionId, input).then((response) => {
      // Añadir el nuevo mensaje en estado inicial
      setMessages((prevMessages) => [...prevMessages, response]);

      // Encolar el proceso
      enqueueGenerativeProcessJob(response.id).then(() => {
        startJobQueue(true).then(() => {
          // Aquí NO arrancamos polling manual,
          // el useEffect se encargará de actualizar este mensaje
          setIsLoadingMessage(false);
        });
      });
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
    if (messages.length === 0) return;

    const POLL_INTERVAL = 1500;

    const intervalId = setInterval(() => {
      const unfinished = messages.filter(
        (m) =>
          getRunStatus(m.status) !== "Finished" &&
          getRunStatus(m.status) !== "Error",
      );

      if (unfinished.length === 0) {
        clearInterval(intervalId); // nothing left to poll
        return;
      }

      // Fetch latest status for each unfinished process
      unfinished.forEach((msg) => {
        getProcessById(msg.id).then((process) => {
          const status = getRunStatus(process.status);

          if (status === "Error") {
            enqueueSnackbar(
              `The process has failed. Deleting it...${
                process.output?.[0]?.data ? `\n${process.output[0].data}` : ""
              }`,
              {
                autoHideDuration: 8000,
                style: { whiteSpace: "pre-line" },
              },
            );

            deleteProcessById(process.id).then(() => {
              setMessages((prev) => prev.filter((m) => m.id !== process.id));
            });
          } else {
            // Update progress or final result
            setMessages((prev) =>
              prev.map((m) => (m.id === process.id ? process : m)),
            );
          }
        });
      });
    }, POLL_INTERVAL);

    return () => clearInterval(intervalId); // cleanup
  }, [messages]);

  useEffect(() => {
    console.log('Combining messages and history for display'); // Add here
    console.log('Messages:', messages);
    console.log('TASK NAME:', taskName);
    let messagesObject = messages.map((process) => {
      // Check if there's reference data in the output (only for RAGTask)
      let referenceOutput = null;
      let mainOutput = process.output;
      
      if (taskName === "RAGTask" && process.output && process.output.length > 1) {
        // Look for Dict type output that contains reference information
        const referenceItem = process.output.find(item => item.data_type === "Dict");
        if (referenceItem) {
          console.log('Raw reference data:', referenceItem.data);
          try {
            // The data might be a Python dict string, try to parse it as JSON
            let dataStr = referenceItem.data;
            
            // If it starts with { but isn't valid JSON, it might be a Python dict
            // Try to convert Python dict format to JSON format
            if (dataStr.startsWith('{') && !dataStr.startsWith('{"')) {
              // Replace Python dict format with JSON format
              dataStr = dataStr
                .replace(/'/g, '"')  // Replace single quotes with double quotes
                .replace(/True/g, 'true')  // Replace Python True with JSON true
                .replace(/False/g, 'false')  // Replace Python False with JSON false
                .replace(/None/g, 'null');  // Replace Python None with JSON null
            }
            
            console.log('Processed data string:', dataStr);
            const parsedData = JSON.parse(dataStr);
            referenceOutput = parsedData;
            // Keep only non-Dict outputs as main output
            mainOutput = process.output.filter(item => item.data_type !== "Dict");
          } catch (e) {
            console.log('Could not parse reference data:', e);
            console.log('Original data:', referenceItem.data);
            // If parsing fails, try to extract info using regex as fallback for multiple references
            try {
              const matches = [...referenceItem.data.matchAll(/(\d+):\s*\{\s*['"]?document_id['"]?\s*:\s*(\d+).*?['"]?text['"]?\s*:\s*['"]([^'"]*)['"]/g)];
              if (matches.length > 0) {
                referenceOutput = {};
                matches.forEach((match, index) => {
                  referenceOutput[match[1] || index] = {
                    document_id: parseInt(match[2]),
                    text: match[3]
                  };
                });
                mainOutput = process.output.filter(item => item.data_type !== "Dict");
                console.log('Fallback parsing successful:', referenceOutput);
              }
            } catch (fallbackError) {
              console.log('Fallback parsing also failed:', fallbackError);
            }
          }
        }
      }

      return {
        type: "message",
        timestamp: process.created,
        id: process.id,
        input: process.input,
        output: mainOutput,
        referenceOutput: referenceOutput,
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
      //bgcolor={"background.box"}
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
            {sessionInfo?.name ? sessionInfo.name : "Untitled Session"}{" "}
            {sessionInfo?.description ? ":" : null} {sessionInfo?.description}
          </Typography>

          <Box>
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
                    <>
                      <ChatBubble
                        messages={message.output}
                        sender={"Model"}
                        timestamp={new Date(
                          message.end_time,
                        ).toLocaleTimeString()}
                      />
                      {taskName === "RAGTask" && message.referenceOutput && (
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold', color: 'text.secondary', opacity: 0.8 }}>
                            References:
                          </Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'row', gap: 1, flexWrap: 'wrap' }}>
                            {Object.entries(message.referenceOutput).map(([key, ref], index) => (
                              <Button
                                key={key}
                                variant="contained"
                                size="small"
                                onClick={() => handleOpenReference(ref, key)}
                                sx={{
                                  backgroundColor: 'hsl(179, 100%, 38%) !important',
                                  color: 'white !important',
                                  minWidth: 'auto',
                                  width: 'auto',
                                  flexShrink: 0,
                                  boxShadow: 'none',
                                  '&:hover': {
                                    backgroundColor: 'hsl(179, 100%, 32%) !important',
                                    boxShadow: 'none'
                                  }
                                }}
                              >
                                Reference {index + 1}
                              </Button>
                            ))}
                          </Box>
                        </Box>
                      )}
                    </>
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

      {/* Reference Modal */}
      <TemplateModal
        open={referenceModalOpen}
        handleClose={() => setReferenceModalOpen(false)}
        template={selectedReferenceText}
        title={referenceModalTitle}
        formatText={true}
      />

      <JobQueueWidget />
    </Box>
  );
}
