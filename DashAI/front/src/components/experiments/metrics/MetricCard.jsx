import { Card, CardActionArea, Box, Typography, Chip } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";

const splitColors = {
  train: {
    border: "#4caf50",
    bg: "rgba(76,175,80,0.08)"
  },
  test: {
    border: "#2196f3",
    bg: "rgba(33,150,243,0.08)"
  },
  validation: {
    border: "#ff9800",
    bg: "rgba(255,152,0,0.08)"
  }
};

export default function MetricCard({
  metric,
  isSelected,
  onToggle,
  splitType,
  disabled = false,
}) {
  const colors = splitColors[splitType];

  return (
    <Card
      variant="outlined"
      sx={{
        borderWidth: 2,
        borderColor: isSelected ? colors.border : "divider",
        backgroundColor: isSelected ? colors.bg : "background.paper",
        opacity: disabled ? 0.6 : 1,
        transition: "all 0.2s",
        "&:hover": disabled
          ? {}
          : {
              transform: "scale(1.02)",
            },
      }}
    >
      <CardActionArea
        onClick={disabled ? undefined : onToggle}
        disabled={disabled}
        sx={{ p: 2 }}
      >
        {/* Selection indicator */}
        <Box
          sx={{
            position: "absolute",
            top: 12,
            right: 12,
            width: 20,
            height: 20,
            borderRadius: "50%",
            border: "2px solid",
            borderColor: isSelected ? colors.border : "divider",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}
        >
          {isSelected && <CheckIcon fontSize="small" />}
        </Box>

        <Box sx={{ pr: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            <Typography
              variant="h6"
              sx={{ fontFamily: "monospace", fontWeight: 600 }}
            >
              {metric.name}
            </Typography>

            {metric.metadata?.maximize && (
              <Chip
                icon={<TrendingUpIcon />}
                label="maximize"
                size="small"
                variant="outlined"
              />
            )}
          </Box>

          <Typography variant="body2" color="text.secondary">
            {metric.description || "No description available"}
          </Typography>
        </Box>
      </CardActionArea>
    </Card>
  );
}
