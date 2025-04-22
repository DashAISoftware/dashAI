import {
  Box,
  Paper,
  Typography,
  Avatar as MuiAvatar,
  Dialog,
  IconButton,
  Fade,
  useTheme,
  Zoom,
} from "@mui/material";
import { useState } from "react";
import CloseIcon from "@mui/icons-material/Close";

export function ChatBubble({
  message,
  messageType,
  sender = "",
  timestamp,
  isUser = false,
}) {
  const [isImageFullscreen, setIsImageFullscreen] = useState(false);
  const theme = useTheme();

  const handleImageClick = () => {
    if (messageType === "PIL.Image") {
      setIsImageFullscreen(true);
    }
  };

  const handleCloseFullscreen = () => {
    setIsImageFullscreen(false);
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        alignItems: "flex-start",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 2,
        width: "100%",
      }}
    >
      {!isUser && (
        <MuiAvatar
          src={"/dai_circle.png"}
          alt={sender || "User"}
          sx={{ mr: 1, width: 32, height: 32 }}
        />
      )}

      <Box sx={{ maxWidth: "80%" }}>
        {!isUser && sender && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ ml: 1, mb: 0.5, display: "block" }}
          >
            {sender}
          </Typography>
        )}

        <Paper
          sx={{
            backgroundColor: "#374151",
            color: "#fff",
            padding: (theme) => theme.spacing(1.5, 2),
            maxWidth: "100%",
            borderRadius: 2,
            borderTopRightRadius: isUser ? 0 : "inherit",
            borderTopLeftRadius: isUser ? "inherit" : 0,
            position: "relative",
          }}
        >
          {messageType === "str" && (
            <Typography variant="body2" color="text.primary">
              {message}
            </Typography>
          )}
          {messageType === "PIL.Image" && (
            <Box
              onClick={handleImageClick}
              sx={{
                cursor: "pointer",
                "&:hover": {
                  opacity: 0.9,
                },
                transition: theme.transitions.create("opacity"),
              }}
            >
              <img
                src={`data:image/png;base64,${message}`}
                alt="Image"
                style={{
                  maxWidth: "100%",
                  maxHeight: "300px",
                  objectFit: "contain",
                  borderRadius: theme.shape.borderRadius,
                  marginTop: theme.spacing(1),
                }}
              />
            </Box>
          )}
        </Paper>

        {timestamp && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: "block",
              mt: 0.5,
              textAlign: isUser ? "right" : "left",
              px: 1,
            }}
          >
            {timestamp}
          </Typography>
        )}
      </Box>

      {isUser && <MuiAvatar alt="User" sx={{ ml: 1, width: 32, height: 32 }} />}

      {/* Fullscreen Image Dialog */}
      <Dialog
        open={isImageFullscreen}
        onClose={handleCloseFullscreen}
        maxWidth="xl"
        fullWidth
        TransitionComponent={Fade}
        transitionDuration={{
          enter: theme.transitions.duration.enteringScreen,
          exit: theme.transitions.duration.leavingScreen,
        }}
        PaperProps={{
          sx: {
            backgroundColor: "rgba(0, 0, 0, 0.9)",
            boxShadow: "none",
            position: "relative",
            m: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          },
        }}
      >
        <IconButton
          onClick={handleCloseFullscreen}
          sx={{
            position: "absolute",
            top: theme.spacing(2),
            right: theme.spacing(2),
            color: "white",
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            "&:hover": {
              backgroundColor: "rgba(0, 0, 0, 0.7)",
            },
            zIndex: 1,
          }}
          aria-label="close"
          size="large"
        >
          <CloseIcon />
        </IconButton>
        <Zoom in={isImageFullscreen}>
          <Box
            component="img"
            src={
              messageType === "PIL.Image"
                ? `data:image/png;base64,${message}`
                : ""
            }
            alt="Fullscreen Image"
            sx={{
              maxWidth: "90%",
              maxHeight: "90%",
              objectFit: "contain",
              cursor: "pointer",
            }}
            onClick={handleCloseFullscreen}
          />
        </Zoom>
      </Dialog>
    </Box>
  );
}
