import React, { useState } from 'react';
import {
  Box,
  Typography,
  Chip,
  Collapse,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Badge,
  Tooltip,
  Divider,
  ListSubheader,
  Button,
} from '@mui/material';
import {
  ExpandMore,
  ExpandLess,
  Source as SourceIcon,
  Article as ArticleIcon,
  Description as DescriptionIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material';
import DocumentReferencesModal from './DocumentReferencesModal';

const SourcesDisplay = ({ references, onOpenReference, isUser = false }) => {
  const [expanded, setExpanded] = useState(false);
  const [documentModalOpen, setDocumentModalOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [selectedChunks, setSelectedChunks] = useState([]);
  const referenceEntries = Object.entries(references);
  const sourceCount = referenceEntries.length;

  console.log("SourcesDisplay - references prop:", references);

  const handleToggleExpanded = () => {
    setExpanded(!expanded);
  };

  const handleOpenDocumentModal = (docId, chunks) => {
    setSelectedDocument({ id: docId });
    setSelectedChunks(chunks);
    setDocumentModalOpen(true);
  };

  const handleCloseDocumentModal = () => {
    setDocumentModalOpen(false);
    setSelectedDocument(null);
    setSelectedChunks([]);
  };

  // Group references by document ID
  const groupedReferences = referenceEntries.reduce((acc, [key, ref]) => {
    const docId = ref.document_id;
    if (!acc[docId]) {
      acc[docId] = [];
    }
    acc[docId].push({ key, ...ref });
    return acc;
  }, {});

  // Get document title - fallback to "Document X" if no title available
  const getDocumentTitle = (docId, chunks) => {
    // Check if any chunk has a document_title or document_name
    const firstChunk = chunks[0];
    if (firstChunk.document_title) return firstChunk.document_title;
    if (firstChunk.document_name) return firstChunk.document_name;
    if (firstChunk.title) return firstChunk.title;
    if (firstChunk.name) return firstChunk.name;
    
    // Fallback to generic title
    return `Document ${docId}`;
  };

  return (
    <Box 
      sx={{ 
        mt: 1,
        ml: isUser ? 0 : '40px', // Match avatar (32px) + margin (8px) 
        mr: isUser ? '40px' : 0, // Right margin for user messages
        maxWidth: isUser ? 'calc(80% - 40px)' : 'calc(80% - 40px)', // Match ChatBubble maxWidth minus avatar space
        border: 1, 
        borderColor: 'divider', 
        borderRadius: 1, 
        backgroundColor: 'background.box',
        overflow: 'hidden'
      }}
    >
      {/* Header */}
      <Box 
        sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          p: 1.5,
          backgroundColor: 'action.hover',
          cursor: 'pointer'
        }}
        onClick={handleToggleExpanded}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <SourceIcon fontSize="small" color="primary" />
          <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
            View message sources
          </Typography>
          <Badge 
            badgeContent={sourceCount} 
            color="primary" 
            sx={{
              '& .MuiBadge-badge': {
                fontSize: '0.75rem',
                height: 20,
                minWidth: 20
              }
            }}
          />
        </Box>
        
        <IconButton size="small">
          {expanded ? <ExpandLess /> : <ExpandMore />}
        </IconButton>
      </Box>

      {/* Sources List */}
      <Collapse in={expanded} timeout="auto">
        <List dense disablePadding>
          {Object.entries(groupedReferences).map(([docId, chunks]) => (
            <React.Fragment key={docId}>
              {/* Document Item */}
              <ListItem disablePadding>
                <Box sx={{ 
                    width: '100%', 
                    p: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    backgroundColor: "background.box",

                }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <DescriptionIcon fontSize="small" color="primary" />
                    <Typography variant="body2">
                      <Typography component="span" sx={{ fontWeight: 'bold' }}>
                        {getDocumentTitle(docId, chunks)}
                      </Typography>
                      {' '}provided{' '}
                      <Typography component="span" sx={{ fontWeight: 'bold' }}>
                        {chunks.length}
                      </Typography>
                      {' '}chunk{chunks.length > 1 ? 's' : ''}
                    </Typography>
                  </Box>
                  
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<VisibilityIcon />}
                    onClick={() => handleOpenDocumentModal(docId, chunks)}
                    sx={{
                      fontSize: '0.75rem',
                      py: 0.5,
                      px: 1,
                    }}
                  >
                    View Chunks
                  </Button>
                </Box>
              </ListItem>

              {/* Divider between documents (but not after the last one) */}
              {Object.keys(groupedReferences).indexOf(docId) < Object.keys(groupedReferences).length - 1 && (
                <Divider />
              )}
            </React.Fragment>
          ))}
        </List>
      </Collapse>

      {/* Document References Modal */}
      <DocumentReferencesModal
        open={documentModalOpen}
        onClose={handleCloseDocumentModal}
        document={selectedDocument}
        chunks={selectedChunks}
        onOpenReference={onOpenReference}
      />
    </Box>
  );
};

export default SourcesDisplay;