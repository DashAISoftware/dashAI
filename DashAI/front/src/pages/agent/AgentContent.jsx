import React, { useState, useEffect} from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  List,
  ListItemButton,
  ListItemText,
  IconButton,
  CircularProgress,
  Alert,
  Paper,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';

import ModuleContainer from "../../components/layout/ModuleContainer";

import { useAgent } from '../../components/agent/contexts/AgentContext';
import AgentLeftBar from '../../components/agent/AgentLeftBar';
import ConversationMessages from '../../components/agent/ConversationMessages';
import AgentRightBar from '../../components/agent/AgentRightBar';
import AgentModalWelcome  from '../../components/agent/AgentModalWelcome';

import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";

import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";

import { useTranslation } from "react-i18next";

const MODAL_DISMISSED_KEY = 'agenticModalDismissed';

export default function AgentContent() {
  const { t } = useTranslation();
  const threePanelLayout = useThreePanelLayout({ storageKey: "agent" });
  const {
    selectedConversationId
  } = useAgent();


  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <AgentModalWelcome />
        <LeftPanel>
          <AgentLeftBar
            onToggle={threePanelLayout.handleToggleLeft}
          />
        </LeftPanel>

        <CenterPanel>
          {selectedConversationId && < ConversationMessages />}
        </CenterPanel>
        {/* Panel derecho: Parámetros de sesión */}
        <RightPanel>
          <AgentRightBar
            onToggle={threePanelLayout.handleToggleRight}
          />
        </RightPanel>
        
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}