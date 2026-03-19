import { useState } from "react";
import { Box, TextField, Button } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import { useTranslation } from "react-i18next";

export function TextInput({ onSendMessage, isLoading }) {
  const [input, setInput] = useState("");
  const { t } = useTranslation(["generative", "common"]);

  const handleSendMessage = () => {
    onSendMessage([input]);
    setInput("");
  };

  return (
    <Box display="flex" alignItems="center" gap={2} width={"100%"}>
      <TextField
        fullWidth
        variant="outlined"
        label={t("generative:label.typeYourMessage")}
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
        disabled={isLoading || !input.trim()}
        data-tour="chat-input"
      >
        {isLoading ? t("common:sending") : t("common:send")}
      </Button>
    </Box>
  );
}

