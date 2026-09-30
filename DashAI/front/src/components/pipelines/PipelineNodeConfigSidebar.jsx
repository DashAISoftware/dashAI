import React from "react";
import { Box, Divider, IconButton, Typography } from "@mui/material";
import SettingsIcon from "@mui/icons-material/Settings";
import CloseIcon from "@mui/icons-material/Close";
import { useTheme } from "@mui/material/styles";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";

function PipelineNodeConfigSidebar({ selectedNode, onClose, children }) {
  const theme = useTheme();
  const nodeTitle =
    selectedNode?.data?.name || selectedNode?.data?.label || selectedNode?.type;

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
          <SettingsIcon
            fontSize="small"
            sx={{ color: theme.palette.text.primary }}
          />
          <Typography variant="subtitle1">
            {nodeTitle ? "Node Configuration" : "Pipeline Node Configuration"}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {selectedNode && (
            <IconButton
              size="small"
              onClick={onClose}
              sx={{ color: "text.secondary" }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
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
        {selectedNode ? (
          children || (
            <Typography variant="body2" color="text.secondary">
              This node does not require configuration.
            </Typography>
          )
        ) : (
          <Typography variant="body2" color="text.secondary">
            Select a node in the canvas to configure it.
          </Typography>
        )}
      </Box>
    </SideBar>
  );
}

export default PipelineNodeConfigSidebar;
