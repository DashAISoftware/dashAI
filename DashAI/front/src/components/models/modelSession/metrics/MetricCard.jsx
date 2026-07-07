import { Card, CardActionArea, Box, Typography, Chip } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import CheckIcon from "@mui/icons-material/Check";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import { useTranslation } from "react-i18next";

export default function MetricCard({
  metric,
  isSelected,
  onToggle,
  splitType,
  disabled = false,
}) {
  const theme = useTheme();

  const splitColors = {
    train: {
      border: theme.palette.chart.train,
      bg: `${theme.palette.chart.train}14`, // ~8% opacity
    },
    test: {
      border: theme.palette.chart.test,
      bg: `${theme.palette.chart.test}14`,
    },
    validation: {
      border: theme.palette.chart.validation,
      bg: `${theme.palette.chart.validation}14`,
    },
  };

  const colors = splitColors[splitType];
  const { t } = useTranslation(["experiments", "common"]);

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
        sx={{ p: 4 }}
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
            justifyContent: "center",
          }}
        >
          {isSelected && <CheckIcon fontSize="small" />}
        </Box>

        <Box sx={{ pr: 6 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
            <Typography variant="h6">{metric.name}</Typography>

            <Chip
              icon={
                metric.metadata.maximize ? (
                  <TrendingUpIcon />
                ) : (
                  <TrendingDownIcon />
                )
              }
              label={
                metric.metadata.maximize
                  ? t("experiments:metrics.maximize")
                  : t("experiments:metrics.minimize")
              }
              size="small"
              variant="outlined"
            />
          </Box>

          <Typography variant="body2" color="text.secondary">
            {metric.description || t("common:noDescription")}
          </Typography>
        </Box>
      </CardActionArea>
    </Card>
  );
}
