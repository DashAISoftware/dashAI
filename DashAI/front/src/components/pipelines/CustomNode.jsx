import { Box, Typography, Tooltip, IconButton } from "@mui/material";
import { Handle, Position } from "reactflow";
import FolderIcon from "@mui/icons-material/Folder";
import InsertChartIcon from "@mui/icons-material/InsertChart";
import SettingsIcon from "@mui/icons-material/Settings";
import EmojiObjectsIcon from "@mui/icons-material/EmojiObjects";
import ManageHistoryIcon from "@mui/icons-material/ManageHistory";
import CloseIcon from "@mui/icons-material/Close";
import { useTheme } from "@mui/material/styles";
import { useState } from "react";

const iconMap = {
  FolderIcon: FolderIcon,
  InsertChartIcon: InsertChartIcon,
  SettingsIcon: SettingsIcon,
  EmojiObjectsIcon: EmojiObjectsIcon,
  ManageHistoryIcon: ManageHistoryIcon,
};

const CustomNode = ({ data, isConnectable }) => {
  const theme = useTheme();
  const [hovered, setHovered] = useState(false);

  const IconComponent = iconMap[data.icon] || SettingsIcon;
  const isDisabled =
    data.errors?.some((err) => err.includes("already exists")) ?? false;
  const borderColor =
    data.notConfigured && !isDisabled
      ? `2px solid ${theme.palette.warning.main}`
      : `1px solid ${theme.palette.ui.borderLight}`;
  const iconColor = isDisabled
    ? theme.palette.text.secondary
    : theme.palette.text.primary;
  const bgColor = isDisabled
    ? theme.palette.ui.panelMedium
    : theme.palette.background.paper;

  const nodeContent = (
    <Box
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      sx={{
        width: 60,
        height: 60,
        alignItems: "center",
        justifyContent: "center",
        display: "flex",
        borderRadius: 2,
        backgroundColor: bgColor,
        border: borderColor,
        textAlign: "center",
        position: "relative",
      }}
    >
      {data.onDelete && hovered && (
        <IconButton
          onClick={(e) => {
            e.stopPropagation();
            data.onDelete();
          }}
          sx={{
            position: "absolute",
            top: 2,
            right: 2,
            padding: "2px",
            zIndex: 2,
            backgroundColor: "transparent",
            "&:hover": {
              backgroundColor: "rgba(0,0,0,0.05)",
            },
          }}
        >
          <CloseIcon
            sx={{ fontSize: 10, color: theme.palette.text.secondary }}
          />
        </IconButton>
      )}

      {data.target && (
        <Handle
          type="target"
          position={Position.Left}
          style={{
            background: isDisabled
              ? theme.palette.ui.border
              : data.hasError
                ? theme.palette.error.main
                : theme.palette.text.primary,
            width: 8,
            height: 8,
            borderRadius: "50%",
          }}
          isConnectable={!isDisabled && isConnectable}
        />
      )}

      <IconComponent sx={{ fontSize: 25, color: iconColor }} />

      {data.source && (
        <Handle
          type="source"
          position={Position.Right}
          style={{
            background: isDisabled
              ? theme.palette.ui.border
              : theme.palette.text.primary,
            width: 8,
            height: 8,
            borderRadius: "50%",
          }}
          isConnectable={!isDisabled && isConnectable}
        />
      )}
    </Box>
  );

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <Typography
        sx={{ fontSize: 11, mb: 1, color: theme.palette.text.primary }}
      >
        {data.name || data.label}
      </Typography>

      {data.notConfigured && !isDisabled ? (
        <Tooltip title="Missing parameters" placement="bottom">
          {nodeContent}
        </Tooltip>
      ) : (
        nodeContent
      )}
    </Box>
  );
};

export default CustomNode;
