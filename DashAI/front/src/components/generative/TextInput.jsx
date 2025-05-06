import { useState } from "react";
import { Box, TextField, Button } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";

export function TextInput({ onSendMessage, isLoading }) {
  const [input, setInput] = useState("");

  const handleSendMessage = () => {
    onSendMessage([input]);
    setInput("");
  };

  return (
    <Box display="flex" alignItems="center" gap={2} width={"100%"}>
      <TextField
        fullWidth
        variant="outlined"
        label="Type a message"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        disabled={isLoading}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !isLoading) {
            e.preventDefault();
            handleSendMessage();
          }
        }}
      />
      <Button
        variant="contained"
        color="primary"
        onClick={handleSendMessage}
        endIcon={<SendIcon />}
        disabled={isLoading}
      >
        {isLoading ? "Sending..." : "Send"}
      </Button>
    </Box>
  );
}

export default TextInput;
