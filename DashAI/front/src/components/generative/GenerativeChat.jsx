import { Box, Divider, IconButton, Typography } from "@mui/material";
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
import SourcesDisplay from "./SourcesDisplay";
import RAGBreadcrumbs from "./RAG/RAGBreadcrumbs";
import { Trans, useTranslation } from "react-i18next";
import { useGenerative } from "./GenerativeContext";
import { useTourContext } from "../tour/TourProvider";
import { useTheme } from "@mui/material/styles";

export default function GenerativeChat() {
  const theme = useTheme();

  const {
    selectedSessionId: sessionId,
    selectedTaskName: taskName,
    paramsVersion,
  } = useGenerative();

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
  const { t } = useTranslation(["generative"]);
  const tourContext = useTourContext();
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  };

  const isAtBottom = () => {
    if (!chatContainerRef.current) return true;
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    return Math.abs(scrollHeight - clientHeight - scrollTop) < 5; // 5px threshold
  };

  const handleScroll = () => {
    setShouldAutoScroll(isAtBottom());
  };

  const handleOpenReference = (ref, key) => {
    const title = `Document ${ref.document_id}${ref.document_name ? ` (${ref.document_name})` : ''}${ref.document_position ? ` - Chunk ${ref.document_position}` : ''}`;
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
    setShouldAutoScroll(true); // Enable auto-scroll when sending new message

    postProcess(sessionId, input).then((response) => {
      // Add the new message to the chat
      setMessages((prevMessages) => [...prevMessages, response]);

      // Enqueue the generative process job
      enqueueGenerativeProcessJob(response.id).then(() => {
        startJobQueue(true).then(() => {
          setIsLoadingMessage(false);
        });
      });

      // End tour if on final step
      if (tourContext?.run && tourContext?.stepIndex === 8) {
        setTimeout(() => {
          tourContext.stopTour();
        }, 100);
      }
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
    if (shouldAutoScroll) {
      scrollToBottom();
    }
  }, [messagesWithHistory, shouldAutoScroll]);

  useEffect(() => {
    if (messages.length === 0) return;

    const POLL_INTERVAL = 1500;

    const intervalId = setInterval(() => {
      const unfinished = messages.filter(
        (m) =>
          m.status !== 3 && // Not Finished
          m.status !== 4, // Not Error
      );

      if (unfinished.length === 0) {
        clearInterval(intervalId); // nothing left to poll
        return;
      }

      // Fetch latest status for each unfinished process
      unfinished.forEach((msg) => {
        getProcessById(msg.id).then((process) => {
          const status = process.status;

          // Error
          if (status === 4) {
            enqueueSnackbar(
              t("generative:error.processError", {
                error: process.output?.[0]?.data
                  ? `\n${process.output[0].data}`
                  : "",
              }),
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
    console.log('session name:', sessionInfo?.name);
    console.log('session description:', sessionInfo?.description);
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
              // Updated regex to capture all fields: document_id, document_name, document_position, text
              const matches = [...referenceItem.data.matchAll(/(\d+):\s*\{\s*['"]?document_id['"]?\s*:\s*(\d+).*?['"]?document_name['"]?\s*:\s*['"]([^'"]*)['"]\s*.*?['"]?document_position['"]?\s*:\s*(\d+).*?['"]?text['"]?\s*:\s*['"]([^'"]*)['"]/gs)];
              console.log('Regex matches for references:', matches);
              
              if (matches.length > 0) {
                referenceOutput = {};
                matches.forEach((match) => {
                  const refId = match[1];
                  referenceOutput[refId] = {
                    document_id: parseInt(match[2]),
                    document_name: match[3],
                    document_position: parseInt(match[4]),
                    text: match[5]
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
      {/* RAG Breadcrumbs - only show for RAG tasks */}
      {taskName === "RAGTask" && (
        <Box sx={{ width: "100%", px: 2, pt: 2 }}>
          <RAGBreadcrumbs sessionName={sessionInfo?.name} />
        </Box>
      )}

      {/* Model display */}
      <Box
        sx={{
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          alignItems: "center",
          borderRadius: 1,
          opacity: 0.5,
          mb: 0.8,
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
                  color: "text.secondary",
                  "&:hover": {
                    color: "text.primary",
                  },
                }}
              />
            </IconButton>
          </Box>
        </Box>
      </Box>

      {/* Model display - hide for RAG tasks since breadcrumbs show session info */}
      {taskName !== "RAGTask" && (
        <>
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
              <Typography variant="title1" gutterBottom>
                {sessionInfo?.name ? sessionInfo.name : "Untitled Session"}{" "}
                {sessionInfo?.description ? ":" : null}
                <br />
                {sessionInfo?.description}
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
        </>
      )}

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
        onScroll={handleScroll}
        sx={{
          "&::-webkit-scrollbar": {
            width: "8px",
          },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: theme.palette.ui.border,
            borderRadius: "4px",
          },
          "&::-webkit-scrollbar-thumb:hover": {
            backgroundColor: theme.palette.ui.hover,
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
                  <Trans i18nKey="generative:label.parameterChangeEvent">
                    Parameters updated: <span>{message.changedMessage}</span>
                  </Trans>
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
                      {taskName === "RAGTask" && message.referenceOutput ? (
                        // For RAG messages, we need custom layout to insert sources before timestamp
                        <>
                          <ChatBubble
                            messages={message.output}
                            sender={"Model"}
                            timestamp={null} // We'll handle timestamp separately
                          />
                          <SourcesDisplay 
                            references={message.referenceOutput}
                            onOpenReference={handleOpenReference}
                            isUser={false}
                          />
                          {/* Add timestamp after sources with proper alignment */}
                          <Box sx={{ 
                            ml: '40px', // Same alignment as sources and message content
                            mt: 1,
                            display: 'flex',
                            justifyContent: 'flex-start'
                          }}>
                            <Box
                              sx={{
                                fontSize: "0.75rem",
                                color: "text.secondary",
                                opacity: 0.7,
                              }}
                            >
                              {new Date(message.end_time).toLocaleTimeString()}
                            </Box>
                          </Box>
                        </>
                      ) : (
                        // For non-RAG messages, use normal ChatBubble with timestamp
                        <ChatBubble
                          messages={message.output}
                          sender={"Model"}
                          timestamp={new Date(
                            message.end_time,
                          ).toLocaleTimeString()}
                        />
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
    </Box>
  );
}
