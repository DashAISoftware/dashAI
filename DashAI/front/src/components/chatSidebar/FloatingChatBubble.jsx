import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Fab,
  Popover,
  List,
  ListItemButton,
  ListItemText,
  ListSubheader,
  Divider,
  Typography,
  Box,
  Tooltip,
  IconButton,
} from "@mui/material";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import AddIcon from "@mui/icons-material/Add";
import SettingsIcon from "@mui/icons-material/Settings";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ChatIcon from "@mui/icons-material/Chat";
import { useChatSidebar } from "./ChatSidebarContext";

export default function FloatingChatBubble() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const {
    sidebarOpen,
    configurations,
    conversations,
    openSidebar,
    fetchConfigurations,
    fetchConversations,
  } = useChatSidebar();

  const [anchorEl, setAnchorEl] = useState(null);
  const [step, setStep] = useState("configurations"); 
  const [selectedConfigId, setSelectedConfigId] = useState(null);

  if (location.pathname.startsWith("/app/agent") || sidebarOpen) {
    return null;
  }

  const handleClick = (e) => {
    fetchConfigurations();
    fetchConversations();
    setAnchorEl(e.currentTarget);

    setStep("configurations");
    setSelectedConfigId(null);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleSelectConfiguration = (configId) => {
    setSelectedConfigId(configId);
    setStep("conversations");
  };

  const handleBackToConfigurations = () => {
    setSelectedConfigId(null);
    setStep("configurations");
  };

  const handleSelectConversation = (conversationId) => {
    handleClose();
    openSidebar(selectedConfigId, conversationId);
  };

  const handleConfigureAgent = () => {
    handleClose();
    navigate("/app/agent");
  };

  const popoverOpen = Boolean(anchorEl);

  const getConversationConfigurationId = (conversation) =>
    conversation.configuration_id ?? conversation.configurationId ?? null;

  const conversationsWithConfiguration = conversations.filter(
    (conv) => getConversationConfigurationId(conv) !== null,
  );

  const filteredConversations = selectedConfigId
    ? conversationsWithConfiguration.length > 0
      ? conversationsWithConfiguration.filter(
          (conv) =>
            `${getConversationConfigurationId(conv)}` === `${selectedConfigId}`,
        )
      : conversations
    : [];

  return (
    <>
      <Tooltip title={t("chatsidebar:bubbleChat")} placement="left">
        <Fab
          color="primary"
          size="large"
          onClick={handleClick}
          sx={{
            position: "fixed",
            bottom: (theme) => theme.spacing(10),
            right: (theme) => theme.spacing(3),
            zIndex: 999,
            width: 72,
            height: 72,
            boxShadow: 6,
            borderRadius: "50%",
            "&:hover": { transform: "scale(1.08)" },
            transition: "transform 0.2s ease",
          }}
        >
          <SmartToyIcon sx={{ fontSize: 32 }} />
        </Fab>
      </Tooltip>

      <Popover
        open={popoverOpen}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        transformOrigin={{ vertical: "bottom", horizontal: "center" }}
        slotProps={{
          paper: {
            sx: { width: 300, maxHeight: 400, borderRadius: 2 },
          },
        }}
      >
        {step === "configurations" ? (
          <>
            <Box sx={{ p: 1.5, pb: 0.5 }}>
              <Typography variant="subtitle1" fontWeight="bold">
                {t("chatsidebar:configurations")}
              </Typography>
            </Box>
            <Divider />
            <List
              dense
              sx={{
                maxHeight: 280,
                overflow: "auto",
                "&::-webkit-scrollbar": { width: "6px" },
                "&::-webkit-scrollbar-thumb": {
                  backgroundColor: "action.disabled",
                  borderRadius: "3px",
                },
              }}
            >
              {configurations.length === 0 ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ p: 2, textAlign: "center" }}
                >
                  {t("chatsidebar:emptyConfigurations")}
                </Typography>
              ) : (
                configurations.map((config) => (
                  <ListItemButton
                    key={config.id}
                    onClick={() => handleSelectConfiguration(config.id)}
                  >
                    <SettingsIcon
                      fontSize="small"
                      sx={{ mr: 1, color: "text.secondary" }}
                    />
                    <ListItemText
                      primary={config.name}
                      primaryTypographyProps={{
                        noWrap: true,
                        fontSize: "0.875rem",
                      }}
                    />
                  </ListItemButton>
                ))
              )}
            </List>
          </>
        ) : (
          <>
            <Box
              sx={{
                p: 1.5,
                pb: 0.5,
                display: "flex",
                alignItems: "center",
              }}
            >
              <IconButton
                size="small"
                onClick={handleBackToConfigurations}
                sx={{ mr: 0.5 }}
              >
                <ArrowBackIcon fontSize="small" />
              </IconButton>
              <Typography variant="subtitle1" fontWeight="bold">
                {t("chatsidebar:conversations")}
              </Typography>
            </Box>
            <Divider />
            <List
              dense
              sx={{
                maxHeight: 280,
                overflow: "auto",
                "&::-webkit-scrollbar": { width: "6px" },
                "&::-webkit-scrollbar-thumb": {
                  backgroundColor: "action.disabled",
                  borderRadius: "3px",
                },
              }}
            >
              {filteredConversations.length === 0 ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ p: 2, textAlign: "center" }}
                >
                  {t("chatsidebar:emptyConversations")}
                </Typography>
              ) : (
                filteredConversations.map((conv) => (
                  <ListItemButton
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                  >
                    <ChatIcon
                      fontSize="small"
                      sx={{ mr: 1, color: "text.secondary" }}
                    />
                    <ListItemText
                      primary={conv.name}
                      primaryTypographyProps={{
                        noWrap: true,
                        fontSize: "0.875rem",
                      }}
                    />
                  </ListItemButton>
                ))
              )}
            </List>
          </>
        )}
        <Divider />
        {step === "configurations" ? (
        <ListItemButton onClick={handleConfigureAgent} sx={{ py: 1.5 }}>
          <AddIcon fontSize="small" sx={{ mr: 1, color: "primary.main" }} />
          <ListItemText
            primary={t("chatsidebar:navigateConfigurationButton")}
            primaryTypographyProps={{
              color: "primary.main",
              fontWeight: "bold",
              fontSize: "0.875rem",
            }}
          />
        </ListItemButton>
        ) : (
        <ListItemButton onClick={handleConfigureAgent} sx={{ py: 1.5 }}>
          <AddIcon fontSize="small" sx={{ mr: 1, color: "primary.main" }} />
          <ListItemText
            primary={t("chatsidebar:navigateConversationButton")}
            primaryTypographyProps={{
              color: "primary.main",
              fontWeight: "bold",
              fontSize: "0.875rem",
            }}
          />
        </ListItemButton>
        )}
      </Popover>
    </>
  );
}
