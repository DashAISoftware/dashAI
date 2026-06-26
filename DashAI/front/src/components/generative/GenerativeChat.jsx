import { Box, Divider, IconButton, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import InfoIcon from "@mui/icons-material/Info";
import ArrowRightAltIcon from "@mui/icons-material/ArrowRightAlt";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { ChatBubble } from "./ChatBubble";
import {
  getProcessById,
  getProcessesBySessionId,
  deleteProcessById,
} from "../../api/process";
import { useState, useEffect, useRef, useMemo } from "react";
import { postProcess } from "../../api/process";
import { enqueueGenerativeProcessJob } from "../../api/job";
import { startJobQueue } from "../../api/job";
import { getHistoryBySessionId, getSessionById } from "../../api/session";
import InfoSessionModal from "./InfoSessionModal";
import { useSnackbar } from "notistack";
import { MediaInput } from "./MediaInput";
import { Trans, useTranslation } from "react-i18next";
import { useGenerative } from "./GenerativeContext";
import { useTourContext } from "../tour/TourProvider";

export default function GenerativeChat() {
  const theme = useTheme();

  const {
    selectedSessionId: sessionId,
    selectedTaskName: taskName,
    tasks,
    paramsVersion,
  } = useGenerative();

  const inputsCardinality = useMemo(() => {
    const task = tasks?.find((t) => t.name === taskName);
    return task?.metadata?.inputs ?? { str: 1 };
  }, [tasks, taskName]);

  const [history, setHistory] = useState([]);
  const [messages, setMessages] = useState([]);
  const [messagesWithHistory, setMessagesWithHistory] = useState([]);
  const [isLoadingMessage, setIsLoadingMessage] = useState(false);
  const chatContainerRef = useRef(null);
  const isAtBottomRef = useRef(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [sessionInfoVisible, setSessionInfoVisible] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["generative"]);
  const tourContext = useTourContext();

  const scrollToBottom = (force = false) => {
    const el = chatContainerRef.current;
    if (!el) return;

    // Force on new message; otherwise only follow if user is already near
    // the bottom, so polling updates don't yank the view down mid read.
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (force || distanceFromBottom <= 100) {
      el.scrollTop = el.scrollHeight;
    }
  };

  const handleScroll = () => {
    const el = chatContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    // Remember the user's position before any content change repaints, so the
    // scroll effect can decide whether to follow without re measuring stale.
    isAtBottomRef.current = distanceFromBottom <= 100;
    setShowScrollButton(distanceFromBottom > 100);
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
    setIsLoadingMessage(true);

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

  const prevMessageCountRef = useRef(0);
  useEffect(() => {
    const isNewMessage =
      messagesWithHistory.length > prevMessageCountRef.current;
    prevMessageCountRef.current = messagesWithHistory.length;
    // Follow on a new message, or when the user was pinned to the bottom
    // before this update (e.g. the model reply replacing the waiting bubble).
    scrollToBottom(isNewMessage || isAtBottomRef.current);
  }, [messagesWithHistory]);

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
      width={"100%"}
      height={"100%"}
      sx={{ overflow: "hidden", minHeight: 0 }}
    >
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
        }}
      >
        <Box
          display="flex"
          flexDirection="row"
          alignItems="center"
          justifyContent="space-between"
          gap={2}
          width={"100%"}
          height={"32px"}
          mb={8}
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

      <Divider sx={{ width: "100%", bgcolor: "divider" }} />

      {/* Chat display */}
      <Box
        sx={{
          position: "relative",
          display: "flex",
          flex: 1,
          minHeight: 0,
          width: "100%",
        }}
      >
        <Box
          display="flex"
          flexDirection="column"
          justifyContent="flex-start"
          alignItems="flex-start"
          gap={4}
          width={"100%"}
          flex={1}
          minHeight={0}
          overflow={"auto"}
          mt={4}
          p={8}
          ref={chatContainerRef}
          onScroll={handleScroll}
        >
          {messagesWithHistory?.map((message) => {
            return (
              <Box
                key={`${message.type}_${message.id}`}
                display="flex"
                flexDirection="column"
                justifyContent="flex-start"
                flexGrow={0}
                gap={4}
                width={"100%"}
                //height={"100%"}
                mt={4}
              >
                {message.type === "history" ? (
                  <Typography variant="body1" sx={{ opacity: 0.8 }}>
                    <Trans i18nKey="generative:label.parameterChangeEvent">
                      Parameters updated: <span>{message.changedMessage}</span>
                    </Trans>
                  </Typography>
                ) : (
                  <>
                    <ChatBubble
                      messages={message.input}
                      sender={"User"}
                      timestamp={new Date(
                        message.timestamp,
                      ).toLocaleTimeString()}
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

        {showScrollButton && (
          <IconButton
            onClick={() => scrollToBottom(true)}
            sx={{
              position: "absolute",
              bottom: 16,
              right: 16,
              bgcolor: "background.paper",
              border: 1,
              borderColor: "divider",
              boxShadow: 2,
              "&:hover": { bgcolor: "background.paper" },
            }}
          >
            <KeyboardArrowDownIcon />
          </IconButton>
        )}
      </Box>

      {/* Chat input */}
      <MediaInput
        key={sessionId}
        onSendMessage={(input) => {
          handleSendMessage(input);
        }}
        isLoading={isLoadingMessage}
        inputsCardinality={inputsCardinality}
      />

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
