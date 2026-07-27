import { useEffect, useState } from "react";
import { TextField, Button, Box } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import { useTranslation } from "react-i18next";

export function MediaInput({
  onSendMessage,
  isLoading = false,
}) {
  const { t } = useTranslation(["agent"]);
  const [text, setText] = useState("");

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setText("");
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        gap: 2,
        flexShrink: 0,
      }}
    >

      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <TextField
        fullWidth
        multiline
        minRows={3}
        maxRows={3}
        placeholder={t("agent:label.typeYourMessage")}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={isLoading}
        variant="outlined"
        onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !isLoading) {
            e.preventDefault();
            handleSend();
            }
        }}

        />

        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1,
            alignItems: "center",
            position: "relative",
          }}
        >

          <Button
            variant="contained"
            color="primary"
            onClick={handleSend}
            disabled={isLoading || !text.trim()}
            sx={{ minWidth: 40, width: 40, height: 40, padding: 0 }}
          >
            <SendIcon />
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
