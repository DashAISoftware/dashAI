import { Box, Typography, Tooltip } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export function HeaderBox({ title, value, IconComponent, iconColor, bgColor }) {
  const theme = useTheme();
  return (
    <Box
      sx={{
        minWidth: "140px",
        flex: "1 1 0",
        borderRadius: 2,
        bgcolor: theme.palette.ui.box,
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        gap: 2,
        p: 2,
        boxShadow: 3,
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 36,
          height: 36,
          borderRadius: 2,
          bgcolor: bgColor,
          flexShrink: 0,
        }}
      >
        <IconComponent style={{ color: iconColor }} />
      </Box>
      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            lineHeight: 1.2,
          }}
        >
          {title}
        </Typography>
        <Tooltip title={value} arrow placement="top-start">
          <Typography
            variant="h5"
            sx={{
              textOverflow: "ellipsis",
              overflow: "hidden",
              whiteSpace: "nowrap",
              width: "100%",
              mt: 0.25,
            }}
          >
            {value}
          </Typography>
        </Tooltip>
      </Box>
    </Box>
  );
}
