
import { useTranslation } from "react-i18next";
import { useAgent } from "./contexts/AgentContext";
import { Box, Divider, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useState, useEffect, useRef } from "react";
import { useSnackbar } from "notistack";

import { ChatBubble } from "../generative/ChatBubble";
import { MediaInput } from "./MediaInput";

import { fetchMessages, 
    enqueueAgenticProcessJob, 
    postProcess, 
    getProcessById, 
    deleteProcessById 
} from "../../api/agent";

export default function ConversationMessages() {
    const { t } = useTranslation();
    const { enqueueSnackbar } = useSnackbar();
    const theme = useTheme();
    const [messages, setMessages] = useState([]);
    const [isLoadingMessage, setIsLoadingMessage] = useState(false);
    const chatContainerRef = useRef(null);

    const {
        selectedConversationId,
        conversationTitle,
        selectedConfigurationId,
    } = useAgent();

    
    const scrollToBottom = () => {
        if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop =
                chatContainerRef.current.scrollHeight;
        }
    };

    const shouldScrollToBottomRef = useRef(false);

    const getMessages = async () => {
        if (!selectedConversationId) {
            setMessages([]);
            return;
        }
        try {
            const data = await fetchMessages(selectedConversationId);
            setMessages(data);
            shouldScrollToBottomRef.current = true;
        } catch (error) {
            enqueueSnackbar(t("agent:error.fetchMessages"), { variant: "error" });
        }
    };

    const handleSendMessage = async (input) => {
        if (!selectedConversationId) return;
        if (!selectedConfigurationId) {
            enqueueSnackbar(
                t(
                    "agent:error.configurationRequired"
                ),
                { variant: "warning" },
            );
            return;
        }

        setIsLoadingMessage(true);
        try {
            const newProcess = await postProcess(
                selectedConversationId,
                selectedConfigurationId,
                input,
            );
            setMessages((prev) => [...prev, newProcess]);
            shouldScrollToBottomRef.current = true;

            await enqueueAgenticProcessJob(newProcess.id, selectedConfigurationId);
        } catch (error) {
            enqueueSnackbar(t("agent:error.sendMessage"), { variant: "error" });
        } finally {
            setIsLoadingMessage(false);
        }
    };

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
            (m) => m.status !== 3 && m.status !== 4 
        );

        if (unfinished.length === 0) {
            clearInterval(intervalId);
            return;
        }

        unfinished.forEach((msg) => {
            getProcessById(msg.id)
            .then((process) => {
                if (process.status === 4) {
                enqueueSnackbar(
                    t("agent:error.processError", {
                    error: process.output?.text
                        ? `\n${process.output.text}`
                        : "",
                    }),
                    {
                    autoHideDuration: 8000,
                    style: { whiteSpace: "pre-line" },
                    }
                );
                deleteProcessById(process.id).then(() => {
                    setMessages((prev) =>
                    prev.filter((m) => m.id !== process.id)
                    );
                });
                } else {
                setMessages((prev) =>
                    prev.map((m) => (m.id === process.id ? process : m))
                );
                }
            })
            .catch((err) => {
                console.error(`Polling failed for process ${msg.id}:`, err);
            });
        });
        }, POLL_INTERVAL);

        return () => clearInterval(intervalId);
    }, [messages]);

    useEffect(() => {
        getMessages();
    }, [selectedConversationId]);

    return (
    <Box
        display="flex"
        flexDirection="column"
        justifyContent="flex-start"
        alignItems="center"
        gap={1}
        width={"100%"}
        height={"100%"}
        sx={{ overflow: "hidden", minHeight: 0 }}
    >
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
            {conversationTitle ? conversationTitle : "Untitled conversation"}
            </Typography>
        </Box>
        </Box>

        <Divider sx={{ width: "100%" }} />

        <Box
        display="flex"
        flexDirection="column"
        justifyContent="flex-start"
        alignItems="flex-start"
        gap={1}
        width={"100%"}
        flex={1}
        minHeight={0}
        overflow={"auto"}
        mt={1}
        p={2}
        ref={chatContainerRef}
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
        {messages?.map((message) => {
            const inputMessage = message.input?.find((msg) => msg.is_input) || message.input?.[0];
            const outputMessage = message.output?.find((msg) => !msg.is_input) || message.output?.[0];

            return (
            <Box
                key={`${message.id}`}
                display="flex"
                flexDirection="column"
                justifyContent="flex-start"
                flexGrow={0}
                gap={1}
                width={"100%"}
                //height={"100%"}
                mt={1}
            >
                <>
                    {!!inputMessage?.text && (
                      <ChatBubble
                          messages={[{
                              id: inputMessage.id,
                              data_type: "str",
                              data: inputMessage.text
                          }]}
                          sender={"User"}
                          timestamp={new Date(message.start_time).toLocaleTimeString()}
                          isUser={true}
                      />
                    )}
                    {!!outputMessage?.text ? (
                        <ChatBubble
                            messages={[{
                                id: outputMessage.id,
                                data_type: "str",
                                data: outputMessage.text
                            }]}
                            sender={"Model"}
                            timestamp={new Date(message.end_time).toLocaleTimeString()}
                        />
                    ) : (
                    <ChatBubble isWaiting={true} sender="Model" />
                    )}
                </>
            </Box>
            );
        })}
        </Box>

        <MediaInput
        key={selectedConversationId}
        onSendMessage={(input) => {
            handleSendMessage(input);
        }}
        isLoading={isLoadingMessage}
        />
    </Box>
    );    
}
