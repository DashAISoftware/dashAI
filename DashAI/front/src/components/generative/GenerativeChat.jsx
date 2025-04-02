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

export default function GenerativeChat() {
  const [message, setMessage] = React.useState("");

  const handleSend = () => {
    // Handle sending the message here
    console.log("Message sent:", message);
    setMessage(""); // Clear the input field after sending
  };

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
            {"Model name"} : {"Model Description"}
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
        Lorem ipsum dolor sit amet consectetur adipisicing elit. Repellendus
        blanditiis, dolores ipsum unde voluptatem consectetur accusamus
        explicabo ex repudiandae voluptas vitae consequatur ea recusandae aut
        distinctio officiis deleniti sint maiores!
      </Box>

      {/* Chat input */}
      <Box display="flex" alignItems="center" gap={2} width={"100%"}>
        <TextField
          fullWidth
          variant="outlined"
          label="Type a message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <Button
          variant="contained"
          color="primary"
          onClick={handleSend}
          endIcon={<SendIcon />}
        >
          Send
        </Button>
      </Box>
    </Box>
  );
}
