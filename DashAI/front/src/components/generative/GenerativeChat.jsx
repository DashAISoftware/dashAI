import {
  Box,
  Divider,
  IconButton,
  Typography,
  TextField,
  Button,
} from "@mui/material";
import React from "react";
import InfoIcon from "@mui/icons-material/Info";
import SendIcon from "@mui/icons-material/Send";
import { ChatBubble } from "./ChatBubble";
import { getProcesses } from "../../api/process";
import { useState, useEffect } from "react";

export default function GenerativeChat({ sessionId }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);

  const getMessages = () => {
    getProcesses(sessionId).then((response) => {
      setMessages(response);
    });
  };

  useEffect(() => {
    getMessages();
  }, []);

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
            {"Model name"} {sessionId} : {"Model Description"}
          </Typography>
          <IconButton>
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

      <Divider sx={{ width: "100%" }} />

      {/* Chat display */}
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="flex-start"
        gap={1}
        width={"100%"}
        height={"100%"}
        overflow={"auto"}
        mt={1}
        p={2}
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
        {/* <ChatBubble
          message="Hi! I need help with my project."
          sender="User"
          timestamp={new Date().toLocaleTimeString()}
          isUser={true}
        />
        <ChatBubble
          message="Hello! How can I assist you today?"
          sender="Model"
          timestamp={new Date().toLocaleTimeString()}
        /> */}
        {messages.map((process) => {
          return (
            <Box
              display="flex"
              flexDirection="column"
              justifyContent="flex-start"
              gap={1}
              width={"100%"}
              height={"100%"}
              mt={1}
            >
              <ChatBubble
                message={process.input}
                sender={"User"}
                timestamp={new Date(process.created).toLocaleTimeString()}
                isUser={true}
              />
              {process.status === 3 ? (
                <ChatBubble
                  message={process.output}
                  sender={"Model"}
                  timestamp={process.end_time}
                />
              ) : (
                <ChatBubble message={"..."} sender="Model"></ChatBubble>
              )}
            </Box>
          );
        })}
      </Box>

      {/* Chat input */}
      <Box display="flex" alignItems="center" gap={2} width={"100%"}>
        <TextField
          fullWidth
          variant="outlined"
          label="Type a message"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <Button
          variant="contained"
          color="primary"
          onClick={() => setInput("")}
          endIcon={<SendIcon />}
        >
          Send
        </Button>
      </Box>
    </Box>
  );
}
