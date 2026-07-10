import { useEffect, useMemo, useRef, useState } from "react";
import { 
  Box, 
  Typography, 
  Button, 
  Chip, 
  Grid, 
  Card, 
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Collapse,
  TextField
} from "@mui/material";
import ChatIcon from "@mui/icons-material/Chat";
import SettingsIcon from "@mui/icons-material/Settings";
import InfoIcon from "@mui/icons-material/Info";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ContentCutIcon from "@mui/icons-material/ContentCut";
import LeaderboardIcon from "@mui/icons-material/Leaderboard";
import BoltIcon from "@mui/icons-material/Bolt";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import EditIcon from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { getGenerativeSession } from "../../../api/generativeTask";
import { updateGenerativeSession, getSessions } from "../../../api/session";
import RAGBreadcrumbs from "./RAGBreadcrumbs";

export default function RAGSessionSummary({
  sessionId,
  onStartChat,
}) {
  const { t } = useTranslation(["generative"]);
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editingName, setEditingName] = useState("");
  const [nameError, setNameError] = useState("");
  const [editingDescription, setEditingDescription] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    chunking: false,
    retriever: false,
    generation: false
  });
  const { enqueueSnackbar } = useSnackbar();
  const originalMetadataRef = useRef({ name: "", description: "" });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const hasMetadataChanges = useMemo(() => {
    const normalizedName = (editingName || "").trim();
    const normalizedDescription = editingDescription || "";
    const originalName = originalMetadataRef.current.name || "";
    const originalDescription = originalMetadataRef.current.description || "";

    return normalizedName !== originalName || normalizedDescription !== originalDescription;
  }, [editingDescription, editingName]);

  // Toggle edit mode
  const handleToggleEditMode = () => {
    if (!isEditing && sessionData) {
      const currentName = sessionData.name || "";
      const currentDescription = sessionData.description || "";
      originalMetadataRef.current = {
        name: currentName,
        description: currentDescription,
      };
      setEditingName(currentName);
      setEditingDescription(currentDescription);
      setNameError("");
    }
    setIsEditing(!isEditing);
  };

  const handleSaveMetadata = async () => {
    if (!sessionData) return;
    if (!hasMetadataChanges || isSaving) return;

    const newName = (editingName || "").trim();
    if (!newName) {
      setNameError(t("generative:rag.validation.nameRequired"));
      enqueueSnackbar(t("generative:rag.validation.nameRequired"), { variant: "error" });
      return;
    }

    try {
      setIsSaving(true);

      // Validate uniqueness: no other session (different id) should have the same name
      const allSessions = await getSessions();
      const duplicate = allSessions.find((s) => s.name === newName && s.id !== sessionData.id);
      if (duplicate) {
        setNameError(t("generative:rag.validation.nameUnique"));
        enqueueSnackbar(t("generative:rag.validation.nameUnique"), { variant: "error" });
        setIsSaving(false);
        return;
      }

      await updateGenerativeSession({
        id: String(sessionData.id),
        formData: {
          name: newName,
          description: editingDescription,
        },
      });

      setSessionData({
        ...sessionData,
        name: newName,
        description: editingDescription,
      });
      originalMetadataRef.current = {
        name: newName,
        description: editingDescription || "",
      };

      setIsEditing(false);
      enqueueSnackbar(t("generative:rag.summary.sessionUpdated"), {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar(t("generative:rag.summary.failedToUpdateSession"), {
        variant: "error",
      });
      console.error("Failed to update session metadata:", error);
    } finally {
      setIsSaving(false);
    }
  };

  // Helper function to determine if a parameter should be shown inline or in modal
  const isSimpleParameter = (value) => {
    return (
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean' ||
      value === null ||
      value === undefined ||
      (Array.isArray(value) && value.length <= 3 && value.every(item => typeof item !== 'object'))
    );
  };

  const formatSimpleValue = (value) => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'boolean') return value.toString();
    if (Array.isArray(value)) return `[${value.join(', ')}]`;
    return String(value);
  };

  const isApiKey = (key) => {
    return key.toLowerCase().includes('api');
  };

  const maskApiKey = (value) => {
    const stringValue = String(value);
    if (stringValue.length <= 10) return stringValue;
    return stringValue.substring(0, 15) + '...';
  };

  const handleCopyToClipboard = (value) => {
    navigator.clipboard.writeText(String(value)).then(() => {
      enqueueSnackbar(t("generative:rag.summary.apiKeyCopied"), { variant: "success" });
    }).catch(() => {
      enqueueSnackbar(t("generative:rag.summary.failedToCopyApiKey"), { variant: "error" });
    });
  };

  const handleParameterClick = (paramName, paramValue, componentName) => {
    setModalContent({
      title: t("generative:rag.summary.parameterDetailTitle", { component: componentName, param: paramName }),
      content: paramValue
    });
    setModalOpen(true);
  };

  const renderParametersList = (params, componentName) => {
    if (!params || Object.keys(params).length === 0) {
      return (
        <Typography variant="caption" color="text.primary" sx={{ ml: 1 }}>
          {t("generative:rag.summary.noParameters")}
        </Typography>
      );
    }

    return Object.entries(params).map(([key, value]) => {
      const isSimple = isSimpleParameter(value);
      const isAPI = isApiKey(key);
      
      return (
        <Box key={key} display="flex" alignItems="center" sx={{ ml: 1, mb: 0.25 }}>
          <Typography variant="caption" color="text.secondary">
            • {key}: 
          </Typography>
          {isSimple ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 0.5 }}>
              <Typography variant="caption" color="text.secondary">
                {isAPI ? maskApiKey(value) : formatSimpleValue(value)}
              </Typography>
              {isAPI && (
                <IconButton
                  size="small"
                  onClick={() => handleCopyToClipboard(value)}
                  sx={{
                    p: 0.25,
                    minWidth: 'auto',
                    color: 'text.secondary',
                    '&:hover': {
                      color: 'primary.main',
                      backgroundColor: 'action.hover'
                    }
                  }}
                  title={t("generative:rag.summary.apiKeyCopied")}
                >
                  <ContentCopyIcon sx={{ fontSize: '0.75rem' }} />
                </IconButton>
              )}
            </Box>
          ) : (
            <Button
              variant="text"
              size="small"
              startIcon={<InfoIcon sx={{ fontSize: '0.75rem' }} />}
              onClick={() => handleParameterClick(key, value, componentName)}
              sx={{ 
                ml: 0.5, 
                p: 0.25,
                minHeight: 'auto',
                textTransform: 'none',
                color: 'primary.main',
                '&:hover': {
                  backgroundColor: 'action.hover'
                }
              }}
            >
              {t("generative:rag.summary.viewDetails")}
            </Button>
          )}
        </Box>
      );
    });
  };

  const CollapsibleParameterCard = ({ icon, title, component, params, sectionKey, componentName }) => (
    <Box 
      sx={{ 
        border: 1, 
        borderColor: 'divider', 
        borderRadius: 1, 
        backgroundColor: 'background.box',
        mt: 2,
        overflow: 'hidden',
        mb: 2
      }}
    >
      {/* Header */}
      <Box 
        sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          p: 2,
          backgroundColor: 'background.box',
          cursor: 'pointer'
        }}
        onClick={() => toggleSection(sectionKey)}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2">{icon}</Typography>
          <Typography variant="subtitle1">
            {title}: <Typography component="span" color="text.primary">{component}</Typography>
          </Typography>
        </Box>
        
        <IconButton size="small">
          <ExpandMoreIcon 
            sx={{ 
              transform: expandedSections[sectionKey] ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s'
            }} 
          />
        </IconButton>
      </Box>

      <Collapse in={expandedSections[sectionKey]} timeout="auto">
        <Box sx={{ p: 2, pt: 1, backgroundColor: 'background.box' }}>
          {renderParametersList(params, componentName)}
        </Box>
      </Collapse>
    </Box>
  );

  useEffect(() => {
    const fetchSessionData = async () => {
      if (!sessionId) return;

      try {
        setLoading(true);
        const session = await getGenerativeSession(sessionId);
        setSessionData(session);
      } catch (error) {
        enqueueSnackbar(t("generative:error.failedToFetchSessionInfo"), {
          variant: "error",
        });
        console.error("Failed to fetch session data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchSessionData();
  }, [sessionId, enqueueSnackbar, t]);

  if (loading) {
    return (
      <Box
        display="flex"
        alignItems="center"
        justifyContent="center"
        height="100%"
      >
        <Typography variant="h6" color="text.secondary">
          {t("generative:rag.summary.loading")}
        </Typography>
      </Box>
    );
  }

  if (!sessionData) {
    return (
      <Box
        display="flex"
        alignItems="center"
        justifyContent="center"
        height="100%"
      >
        <Typography variant="h6" color="text.secondary">
          {t("generative:rag.summary.sessionNotFound")}
        </Typography>
      </Box>
    );
  }

  const parameters = sessionData.parameters || {};

  return (
    <Box
      display="flex"
      flexDirection="column"
      height="100%"
      px={3}
      gap={3}
      overflow="auto"
    >
      {/* RAG Breadcrumbs */}
      <RAGBreadcrumbs sessionName={sessionData?.name} />

      <Box 
        display="flex" 
        width="100%"
        justifyContent="space-between"
        alignItems="flex-start"
        paddingBottom={2}
        gap={2}
      >
        {/* Left: Session Info (Editable/Readable) */}
        <Box flexGrow={1} display="flex" flexDirection="column">
          {isEditing ? (
            <Box display="flex" flexDirection="column" gap={2}>
              <TextField
                fullWidth
                label={t("generative:rag.summary.sessionName")}
                value={editingName}
                onChange={(e) => {
                  setEditingName(e.target.value);
                  // clear inline error while typing
                  if (nameError) setNameError("");
                }}
                error={Boolean(nameError)}
                helperText={nameError}
                variant="outlined"
                size="small"
              />
              <TextField
                fullWidth
                label={t("generative:rag.summary.sessionDescription")}
                value={editingDescription}
                onChange={(e) => setEditingDescription(e.target.value)}
                variant="outlined"
                size="small"
                multiline
                rows={2}
              />
            </Box>
          ) : (
            <>
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="h4" gutterBottom sx={{ mr: 1 }}>
                  {sessionData.name}
                </Typography>
                <IconButton
                  size="small"
                  onClick={handleToggleEditMode}
                  sx={{ color: 'text.secondary' }}
                  aria-label={t("generative:rag.summary.edit")}
                >
                  <EditIcon fontSize="small" />
                </IconButton>
              </Box>
              <Typography variant="body1" color="text.secondary" mb={2}>
                {sessionData.description || t("generative:rag.summary.descriptionPlaceholder")}
              </Typography>
              <Box display="flex" gap={1}>
                <Chip 
                  label={t("generative:rag.summary.title")} 
                  color="text.secondary" 
                  variant="outlined"
                  size="small"
                  sx={{ color: 'text.secondary' }}
                />
                <Chip 
                  label={`${t("generative:rag.summary.createdLabel")} ${new Date(sessionData.created).toLocaleDateString()}`}
                  variant="outlined"
                  size="small"
                  color="text.secondary"
                  sx={{ color: 'text.secondary' }}
                />
              </Box>
            </>
          )}
        </Box>

        {/* Right: Action Buttons */}
        <Box display="flex" flexDirection="column" gap={1} alignItems="flex-end">
          {isEditing ? (
            <>
              <Button
                variant="contained"
                color="primary"
                onClick={handleSaveMetadata}
                disabled={isSaving || !hasMetadataChanges}
                aria-label={t("generative:rag.summary.save")}
                sx={{ minWidth: 40, width: 40, height: 40, padding: 0 }}
              >
                <SaveIcon fontSize="small" />
              </Button>
              <IconButton
                size="small"
                onClick={handleToggleEditMode}
                disabled={isSaving}
                aria-label={t("generative:rag.summary.cancel")}
                sx={{ color: 'text.secondary' }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </>
          ) : (
            <Button
              variant="contained"
              size="large"
              startIcon={<ChatIcon />}
              onClick={onStartChat}
              sx={{
                py: 1.5,
                px: 4,
                borderRadius: 2,
                boxShadow: 3,
                textTransform: 'none',
                '&:hover': {
                  boxShadow: 6,
                  transform: 'translateY(-1px)',
                },
                transition: 'all 0.2s ease-in-out'
              }}
            >
              {t("generative:rag.summary.openChatButton")}
            </Button>
          )}
        </Box>
      </Box>

      <Grid container spacing={3} sx={{ width: '100%' }}>
        <Grid item sx={{ backgroundColor: 'background.box', width: '100%' }}>
          <Card sx={{ backgroundColor: 'background.box' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={3}>
                <SettingsIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">
                  {t("generative:rag.summary.detailedConfig")}
                </Typography>
              </Box>
              
              {parameters.chunking_model && (
                <CollapsibleParameterCard
                  icon={<ContentCutIcon fontSize="small" sx={{ color: 'text.secondary' }} />}
                  title={t("generative:rag.summary.chunkingModel")}
                  component={parameters.chunking_model.component}
                  params={parameters.chunking_model.params}
                  sectionKey="chunking"
                  componentName={t("generative:rag.summary.chunkingModel")}
                />
              )}

              {parameters.retriever_model && (
                <CollapsibleParameterCard
                  icon={<LeaderboardIcon fontSize="small" sx={{ color: 'text.secondary' }} />}
                  title={t("generative:rag.summary.retrieverModel")}
                  component={parameters.retriever_model.component}
                  params={parameters.retriever_model.params}
                  sectionKey="retriever"
                  componentName={t("generative:rag.summary.retrieverModel")}
                />
              )}

              {parameters.generation_model && (
                <CollapsibleParameterCard
                  icon={<BoltIcon fontSize="small" sx={{ color: 'text.secondary' }} />}
                  title={t("generative:rag.summary.generationModel")}
                  component={parameters.generation_model.component}
                  params={parameters.generation_model.params}
                  sectionKey="generation"
                  componentName={t("generative:rag.summary.generationModel")}
                />
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Dialog
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              {modalContent?.title || t("generative:rag.summary.parameterDetails")}
            </Typography>
            <IconButton onClick={() => setModalOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {t("generative:rag.summary.completeConfig")}
            </Typography>
            <Box
              component="pre"
              sx={{
                bgcolor: 'background.paper',
                color: 'text.secondary',
                p: 2,
              }}
            >
              {modalContent?.content ? JSON.stringify(modalContent.content, null, 2) : ''}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModalOpen(false)}>{t("generative:rag.summary.close")}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
