import { Box, Typography, Tooltip } from '@mui/material';
import { Handle, Position } from 'reactflow';
import FolderIcon from '@mui/icons-material/Folder';
import InsertChartIcon from '@mui/icons-material/InsertChart';
import SettingsIcon from '@mui/icons-material/Settings';
import EmojiObjectsIcon from '@mui/icons-material/EmojiObjects';
import { useTheme } from '@mui/material/styles';

const iconMap = {
  FolderIcon: FolderIcon,
  InsertChartIcon: InsertChartIcon,
  SettingsIcon: SettingsIcon,
  EmojiObjectsIcon: EmojiObjectsIcon,
};

const CustomNode = ({ data, isConnectable }) => {
  const theme = useTheme();
  const IconComponent = iconMap[data.icon] || FolderIcon;
  const isDisabled = data.errors?.some(err => err.includes("already exists")) ?? false;
  const borderColor = data.notConfigured && !isDisabled
    ? `2px solid ${theme.palette.warning.main}`
    : '1px solid #ccc';
  const iconColor = isDisabled ? '#aaa' : '#555';
  const bgColor = isDisabled ? '#f0f0f0' : '#fff';

  const nodeContent = (
    <Box
      sx={{
        width: 70,
        height: 70,
        alignItems: 'center',
        justifyContent: 'center',
        display: 'flex',
        borderRadius: 2,
        backgroundColor: bgColor,
        border: borderColor,
        textAlign: 'center',
        position: 'relative',
      }}
    >
      {!isDisabled && data.target && (
        <Handle
          type="target"
          position={Position.Left}
          style={{
            background: data.hasError ? theme.palette.error.main : '#555',
            width: 8,
            height: 8,
            borderRadius: '50%',
          }}
          isConnectable={isConnectable}
        />
      )}

      <IconComponent sx={{ fontSize: 30, color: iconColor }} />

      {!isDisabled && data.source && (
        <Handle
          type="source"
          position={Position.Right}
          style={{
            background: '#555',
            width: 8,
            height: 8,
            borderRadius: '50%',
          }}
          isConnectable={isConnectable}
        />
      )}
    </Box>
  );

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      <Typography variant="subtitle2" sx={{ mb: 0.5, color: '#000' }}>
        {data.name}
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
