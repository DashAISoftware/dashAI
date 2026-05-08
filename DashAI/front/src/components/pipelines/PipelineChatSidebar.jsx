import React, { useState } from "react";
import {
  Box,
  Button,
  Divider,
  IconButton,
  TextField,
  Typography,
} from "@mui/material";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { ChevronRight } from "@mui/icons-material";
import { useTheme } from "@mui/material/styles";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";

function PipelineChatSidebar({ onToggle }) {
  const theme = useTheme();
  const [message, setMessage] = useState("");

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          minHeight: 64,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <SmartToyIcon fontSize="small" sx={{ color: theme.palette.text.primary }} />
          <Typography variant="subtitle1">Pipeline Chatbot</Typography>
        </Box>
        {onToggle && (
          <IconButton
            size="small"
            onClick={onToggle}
            sx={{ color: "text.secondary" }}
          >
            <ChevronRight />
          </IconButton>
        )}
      </Box>

      <Divider sx={{ width: "100%", bgcolor: theme.palette.ui.borderDark }} />

      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          p: 2,
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
        }}
      >
        <Box
          sx={{
            p: 1.5,
            borderRadius: 1,
            backgroundColor: theme.palette.background.paper,
            border: `1px dashed ${theme.palette.ui.borderLight}`,
          }}
        >
          <Typography variant="caption" color="text.secondary">
            Ideas de prompts:
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            - "Revisa este pipeline y sugiere mejoras"
          </Typography>
          <Typography variant="body2" color="text.secondary">
            - "Explica por que falla la validacion"
          </Typography>
          <Typography variant="body2" color="text.secondary">
            - "Sugiere el siguiente nodo"
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ width: "100%", bgcolor: theme.palette.ui.borderDark }} />

      <Box sx={{ p: 1.5, display: "flex", gap: 1, alignItems: "flex-end" }}>
        <TextField
          fullWidth
          size="small"
          multiline
          minRows={2}
          maxRows={4}
          placeholder="Escribe un mensaje..."
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />
        <Button variant="contained" disabled>
          Enviar
        </Button>
      </Box>
    </SideBar>
  );
}

export default PipelineChatSidebar;
