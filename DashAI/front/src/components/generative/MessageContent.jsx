import { Box, Paper, Typography, useTheme } from "@mui/material";
import { useTranslation } from "react-i18next";
import { TextMessage } from "./TextMessage";
import { ImageMessage } from "./ImageMessage";
import { AudioMessage } from "./AudioMessage";
import { VideoMessage } from "./VideoMessage";
import LoadingDots from "../shared/LoadingDots";

export function MessageContent({ messages, isUser, isWaiting, isError }) {
  const theme = useTheme();
  const { t } = useTranslation(["generative"]);

  return (
    <Paper
      sx={{
        backgroundColor: theme.palette.ui.box,
        color: "text.primary",
        padding: theme.spacing(1.5, 4),
        maxWidth: "100%",
        borderRadius: 2,
        borderTopRightRadius: isUser ? 0 : "inherit",
        borderTopLeftRadius: isUser ? "inherit" : 0,
        position: "relative",
      }}
    >
      {isWaiting ? (
        <LoadingDots />
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {/* A failed turn says so, then shows the stored error detail. */}
          {isError && (
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {t("generative:error.replyFailed")}
            </Typography>
          )}
          {messages?.map((message) => {
            const type = message["data_type"];
            return (
              <Box key={message.id}>
                {type === "str" && (
                  <TextMessage message={message.data} isError={isError} />
                )}
                {type === "Image" && <ImageMessage image={message.data} />}
                {type === "Audio" && <AudioMessage audio={message.data} />}
                {type === "Video" && <VideoMessage video={message.data} />}
              </Box>
            );
          })}
        </Box>
      )}
    </Paper>
  );
}
