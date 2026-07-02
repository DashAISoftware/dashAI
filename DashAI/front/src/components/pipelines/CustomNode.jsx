import { Box, Typography, Tooltip, IconButton } from "@mui/material";
import { Handle, Position } from "reactflow";
import FolderIcon from "@mui/icons-material/Folder";
import InsertChartIcon from "@mui/icons-material/InsertChart";
import SettingsIcon from "@mui/icons-material/Settings";
import EmojiObjectsIcon from "@mui/icons-material/EmojiObjects";
import ManageHistoryIcon from "@mui/icons-material/ManageHistory";
import CallSplitIcon from "@mui/icons-material/CallSplit";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";
import AssessmentIcon from "@mui/icons-material/Assessment";
import CloseIcon from "@mui/icons-material/Close";
import { useTheme } from "@mui/material/styles";
import { useState } from "react";

const iconMap = {
  FolderIcon: FolderIcon,
  InsertChartIcon: InsertChartIcon,
  SettingsIcon: SettingsIcon,
  EmojiObjectsIcon: EmojiObjectsIcon,
  ManageHistoryIcon: ManageHistoryIcon,
  CallSplitIcon: CallSplitIcon,
  ModelTrainingIcon: ModelTrainingIcon,
  AssessmentIcon: AssessmentIcon,
};

const CustomNode = ({ data, isConnectable }) => {
  const theme = useTheme();
  const [hovered, setHovered] = useState(false);

  const isLightCanvas = data.canvasMode === "light";

  const IconComponent = iconMap[data.icon] || SettingsIcon;
  const isDisabled =
    data.errors?.some((err) => err.includes("already exists")) ?? false;

  const borderColor = isLightCanvas
    ? data.notConfigured && !isDisabled
      ? "2px solid #f9a825"
      : "1px solid #f9a825"
    : data.notConfigured && !isDisabled
      ? `2px solid ${theme.palette.warning.main}`
      : `1px solid ${theme.palette.ui.borderLight}`;

  const iconColor = isLightCanvas
    ? isDisabled
      ? "#999999"
      : "#333333"
    : isDisabled
      ? theme.palette.text.secondary
      : theme.palette.text.primary;

  const bgColor = isLightCanvas
    ? isDisabled
      ? "#f5f5f5"
      : "#ffffff"
    : isDisabled
      ? theme.palette.ui.panelMedium
      : theme.palette.background.paper;

  const textColor = isLightCanvas ? "#1a1a1a" : theme.palette.text.primary;
  const secondaryTextColor = isLightCanvas
    ? "#666666"
    : theme.palette.text.secondary;
  const handleColor = isLightCanvas ? "#333333" : theme.palette.text.primary;
  const handleDisabledColor = isLightCanvas
    ? "#cccccc"
    : theme.palette.ui.border;
  const sourceHandles = Math.max(1, Number(data.sourceHandles) || 1);
  const targetHandles = Math.max(1, Number(data.targetHandles) || 1);

  const getSourceHandleStyle = (index) => {
    if (sourceHandles === 1) {
      return {
        top: "50%",
        transform: "translateY(-50%)",
      };
    }

    const spacing = sourceHandles + 1;
    const top = ((index + 1) / spacing) * 100;
    return {
      top: `${top}%`,
      transform: "translateY(-50%)",
    };
  };

  const getTargetHandleStyle = (index) => {
    if (targetHandles === 1) {
      return {
        top: "50%",
        transform: "translateY(-50%)",
      };
    }

    const spacing = targetHandles + 1;
    const top = ((index + 1) / spacing) * 100;
    return {
      top: `${top}%`,
      transform: "translateY(-50%)",
    };
  };

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
          <CloseIcon sx={{ fontSize: 10, color: secondaryTextColor }} />
        </IconButton>
      )}

      {data.target &&
        Array.from({ length: targetHandles }).map((_, index) => (
          <Handle
            key={`target-${index}`}
            id={index === 0 ? undefined : `target-${index}`}
            type="target"
            position={Position.Left}
            style={{
              ...getTargetHandleStyle(index),
              background: isDisabled
                ? handleDisabledColor
                : data.hasError
                  ? theme.palette.error.main
                  : handleColor,
              width: 8,
              height: 8,
              borderRadius: "50%",
            }}
            isConnectable={!isDisabled && isConnectable}
          />
        ))}

      <IconComponent sx={{ fontSize: 25, color: iconColor }} />

      {data.source &&
        Array.from({ length: sourceHandles }).map((_, index) => (
          <Handle
            key={`source-${index}`}
            id={index === 0 ? undefined : `source-${index}`}
            type="source"
            position={Position.Right}
            style={{
              ...getSourceHandleStyle(index),
              background: isDisabled ? handleDisabledColor : handleColor,
              width: 8,
              height: 8,
              borderRadius: "50%",
            }}
            isConnectable={!isDisabled && isConnectable}
          />
        ))}
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
      <Typography variant="body2" sx={{ mb: 1, color: textColor }}>
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
