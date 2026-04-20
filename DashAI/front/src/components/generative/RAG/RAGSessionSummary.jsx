import { useEffect, useState } from "react";
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  Chip, 
  Grid, 
  Card, 
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Collapse
} from "@mui/material";
import ChatIcon from "@mui/icons-material/Chat";
import DescriptionIcon from "@mui/icons-material/Description";
import SettingsIcon from "@mui/icons-material/Settings";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import InfoIcon from "@mui/icons-material/Info";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ContentCutIcon from "@mui/icons-material/ContentCut";
import LeaderboardIcon from "@mui/icons-material/Leaderboard";
import BoltIcon from "@mui/icons-material/Bolt";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { useSnackbar } from "notistack";
import { getGenerativeSession } from "../../../api/generativeTask";
import { getRAGPrompts } from "../../../api/rag";
import RAGBreadcrumbs from "./RAGBreadcrumbs";

export default function RAGSessionSummary({
  sessionId,
  onStartChat,
}) {
  const [sessionData, setSessionData] = useState(null);
  const [promptData, setPromptData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    chunking: false,
    retriever: false,
    generation: false
  });
  const { enqueueSnackbar } = useSnackbar();

  // Toggle function for collapsible sections
  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
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

  // Helper function to format simple parameter values
  const formatSimpleValue = (value) => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'boolean') return value.toString();
    if (Array.isArray(value)) return `[${value.join(', ')}]`;
    return String(value);
  };

  // Helper function to check if parameter is an API key
  const isApiKey = (key) => {
    return key.toLowerCase().includes('api');
  };

  // Helper function to mask API key values
  const maskApiKey = (value) => {
    const stringValue = String(value);
    if (stringValue.length <= 10) return stringValue;
    return stringValue.substring(0, 15) + '...';
  };

  // Helper function to copy to clipboard
  const handleCopyToClipboard = (value) => {
    navigator.clipboard.writeText(String(value)).then(() => {
      enqueueSnackbar("API key copied to clipboard", { variant: "success" });
    }).catch(() => {
      enqueueSnackbar("Failed to copy API key", { variant: "error" });
    });
  };

  // Helper function to open modal with complex parameter
  const handleParameterClick = (paramName, paramValue, componentName) => {
    setModalContent({
      title: `${componentName} - ${paramName}`,
      content: paramValue
    });
    setModalOpen(true);
  };

  // Helper function to render parameter list with modal support
  const renderParametersList = (params, componentName) => {
    if (!params || Object.keys(params).length === 0) {
      return (
        <Typography variant="caption" color="text.primary" sx={{ ml: 1 }}>
          No parameters
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
                  title="Copy API key"
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
                fontSize: '0.75rem',
                textTransform: 'none',
                color: 'primary.main',
                '&:hover': {
                  backgroundColor: 'action.hover'
                }
              }}
            >
              View Details
            </Button>
          )}
        </Box>
      );
    });
  };

  // Component for collapsible parameter card
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, backgroundColor: 'background.box' }}>
          <Typography variant="body2">{icon}</Typography>
          <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
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

      {/* Parameters List */}
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
        
        // Fetch session data
        const session = await getGenerativeSession(sessionId);
        setSessionData(session);

        // Fetch prompt data if prompt_id exists
        if (session.parameters?.prompt_id) {
          const prompts = await getRAGPrompts();
          const prompt = prompts.find(p => p.id === session.parameters.prompt_id);
          setPromptData(prompt);
        }
      } catch (error) {
        enqueueSnackbar("Failed to fetch session data", {
          variant: "error",
        });
        console.error("Failed to fetch session data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchSessionData();
  }, [sessionId, enqueueSnackbar]);

  if (loading) {
    return (
      <Box
        display="flex"
        alignItems="center"
        justifyContent="center"
        height="100%"
      >
        <Typography variant="h6" color="text.secondary">
          Loading session data...
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
          Session not found
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
      {/* Header */}
      <Box 
        display="flex" 
        width="100%"
        justifyContent="space-between"
        alignItems="center"
        paddingBottom={2}
        >
        <Box flexGrow={1} mr={2}>
          <Typography variant="h4" gutterBottom>
            {sessionData.name}
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={2}>
            {sessionData.description || "No description available"}
          </Typography>
          <Box display="flex" gap={1}>
            <Chip 
              label="RAG Session" 
              color="text.secondary" 
              variant="outlined"
              size="small"
              sx={{ color: 'text.secondary' }}
            />
            <Chip 
              label={`Created ${new Date(sessionData.created).toLocaleDateString()}`}
              variant="outlined"
              size="small"
              color="text.secondary"
              sx={{ color: 'text.secondary' }}
            />
          </Box>
        </Box>
        
        <Button
          variant="contained"
          size="large"
          startIcon={<ChatIcon />}
          onClick={onStartChat}
          sx={{
            py: 1.5,
            px: 4,
            fontSize: '1rem',
            fontWeight: 600,
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
          Open RAG session chat
        </Button>
      </Box>

      {/* Main Content Grid */}
      <Grid container spacing={3} sx={{ flex: 1 }}>
        {/* Documents Card */}
        {/* <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', backgroundColor: 'background.box' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <DescriptionIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">
                  Documents
                </Typography>
              </Box>
              <Typography variant="h4" color="text.primary" gutterBottom align="center">
                {parameters.documents?.length || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {parameters.documents?.length === 1 ? 'document' : 'documents'} selected for retrieval
              </Typography>
            </CardContent>
          </Card>
        </Grid> */}

        {/* Pipeline Configuration Card */}
        {
            false && (
            <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%', backgroundColor: 'background.box' }}>
                <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                    <SettingsIcon sx={{ mr: 1 }} />
                    <Typography variant="h6">
                    Pipeline Models
                    </Typography>
                </Box>
                <Box sx={{ backgroundColor: 'background.paper', p: 1, borderRadius: 1 }}>
                    {parameters.chunking_model && (
                    <Typography variant="body2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <ContentCutIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                        <strong>Chunking:</strong>&nbsp;{parameters.chunking_model.component}
                    </Typography>
                    )}
                    {parameters.retriever_model && (
                    <Typography variant="body2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LeaderboardIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                        <strong>Retriever:</strong>&nbsp;{parameters.retriever_model.component}
                    </Typography>
                    )}
                    {parameters.generation_model && (
                    <Typography variant="body2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <BoltIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                        <strong>Generator:</strong>&nbsp;{parameters.generation_model.component}
                    </Typography>
                    )}

                </Box>
                </CardContent>
            </Card>
            </Grid>
            )
        }
        {/* Detailed Configuration - Collapsible Cards */}
    <Grid item  sx ={{ backgroundColor: 'background.box', width: '100%'}}>
            <Card sx={{ height: '100%', backgroundColor: 'background.box' }}>
              <CardContent>
            <Box display="flex" alignItems="center" mb={3}>
              <SettingsIcon sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6">
                Detailed Configuration
              </Typography>
            </Box>
            
            {/* Chunking Model */}
            {parameters.chunking_model && (
              <CollapsibleParameterCard
                icon={<ContentCutIcon fontSize="small" sx={{ color: 'text.secondary' }} />}
                title="Chunking Model"
                component={parameters.chunking_model.component}
                params={parameters.chunking_model.params}
                sectionKey="chunking"
                componentName="Chunking Model"
              />
            )}

            {/* Retriever Model */}
            {parameters.retriever_model && (
              <CollapsibleParameterCard
                icon={<LeaderboardIcon fontSize="small" sx={{ color: 'text.secondary' }} />}
                title="Retriever Model"
                component={parameters.retriever_model.component}
                params={parameters.retriever_model.params}
                sectionKey="retriever"
                componentName="Retriever Model"
              />
            )}

            {/* Generation Model */}
            {parameters.generation_model && (
              <CollapsibleParameterCard
                icon={<BoltIcon fontSize="small" sx={{ color: 'text.secondary' }} />}
                title="Generation Model"
                component={parameters.generation_model.component}
                params={parameters.generation_model.params}
                sectionKey="generation"
                componentName="Generation Model"
              />
            )}
              </CardContent>
            </Card>
        </Grid>

        {/* Prompt Configuration */}
        <Grid item width="100%">
          <Paper elevation={1} sx={{ p: 3, backgroundColor: 'background.box' }}>
            <Box display="flex" alignItems="center" mb={2}>
                <AutoFixHighIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">
                  Prompt selected
                </Typography>
              </Box>
            
            {promptData ? (
              <Box>
                <Typography variant="body1">
                  <span style={{ color: 'text.secondary'}}>
                    Name: 
                </span>
                <span style={{ color: 'text.primary'}}>
                    {promptData.name}
                </span>
                </Typography>
                {promptData.parameters?.template && (
                  <Box>
                    <Typography variant="body1" fontWeight="medium" mb={1} color="text.secondary">
                      Template:
                    </Typography>
                    <Box
                      component="pre"
                      sx={{
                        fontSize: 'body1',
                        bgcolor: 'background.box',
                        color: 'text.secondary',
                        p: 2,
                        borderRadius: 1,
                        overflow: 'auto',
                        maxHeight: '200px',
                        whiteSpace: 'pre-wrap',
                        border: '1px solid',
                        borderColor: 'grey.300',
                        fontFamily: 'monospace'
                      }}
                    >
                      {promptData.parameters.template}
                    </Box>
                  </Box>
                )}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No prompt configured
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Parameter Details Modal */}
      <Dialog
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              {modalContent?.title || 'Parameter Details'}
            </Typography>
            <IconButton onClick={() => setModalOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Complete parameter configuration:
            </Typography>
            <Box
              component="pre"
              sx={{
                fontSize: '0.875rem',
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
          <Button onClick={() => setModalOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}