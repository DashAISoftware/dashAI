import React from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Chip,
  Divider,
  Grid,
  Paper,
  Skeleton,
  Typography,
} from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TimelineIcon from "@mui/icons-material/Timeline";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";

/**
 * Displays temporal information about a forecasting model for explainer configuration.
 * Shows training data properties, detected frequency, and explains what the explainer will analyze.
 */
function ForecastingExplainerInfo({
  temporalInfo,
  loading,
  explainerName,
  modelName,
  horizon,
}) {
  if (loading) {
    return (
      <Paper
        elevation={0}
        sx={{
          p: 2,
          bgcolor: "grey.50",
          border: "1px solid",
          borderColor: "grey.200",
          borderRadius: 2,
          mb: 2,
        }}
      >
        <Skeleton variant="text" width="60%" height={28} />
        <Skeleton variant="rectangular" height={100} sx={{ mt: 1 }} />
      </Paper>
    );
  }

  if (!temporalInfo) {
    return null;
  }

  // Get explainer-specific description
  const getExplainerDescription = () => {
    switch (explainerName) {
      case "ForecastDecomposition":
        return {
          title: "Forecast Decomposition",
          icon: <TimelineIcon />,
          color: "primary",
          description: `This explainer will decompose ${horizon || 30} future ${temporalInfo.frequency_label?.toLowerCase() || "periods"} into interpretable components: trend, seasonality, and external factors.`,
          details: [
            "Trend: Shows the long-term direction of your forecast",
            "Seasonality: Reveals repeating patterns (daily, weekly, yearly)",
            "Residuals: Captures unexplained variations",
          ],
        };
      case "ForecastFeatureImportance":
        return {
          title: "Feature Importance",
          icon: <AutoGraphIcon />,
          color: "secondary",
          description:
            "This explainer measures how each external variable (exogenous feature) contributes to forecast accuracy.",
          details: [
            "Permutation-based importance scoring",
            "Shows which features have the most impact",
            "Helps identify which external data to prioritize",
          ],
        };
      case "ForecastUncertainty":
        return {
          title: "Uncertainty Analysis",
          icon: <TrendingUpIcon />,
          color: "warning",
          description: `This explainer will analyze prediction confidence for ${horizon || 30} future ${temporalInfo.frequency_label?.toLowerCase() || "periods"}, showing how uncertainty grows over time.`,
          details: [
            "Confidence intervals for each forecast step",
            "Best/worst case scenario bounds",
            "Critical for risk management and planning",
          ],
        };
      default:
        return {
          title: "Forecasting Explainer",
          icon: <InfoOutlinedIcon />,
          color: "info",
          description: "This explainer will analyze your forecasting model.",
          details: [],
        };
    }
  };

  const explainerInfo = getExplainerDescription();

  return (
    <Box sx={{ mb: 3 }}>
      {/* Model & Training Data Info */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          bgcolor: "success.50",
          border: "1px solid",
          borderColor: "success.200",
          borderRadius: 2,
          mb: 2,
        }}
      >
        <Typography
          variant="subtitle2"
          sx={{ mb: 1.5, display: "flex", alignItems: "center", gap: 1 }}
        >
          <TrendingUpIcon fontSize="small" color="success" />
          Model Training Data Properties
          {modelName && (
            <Chip
              label={modelName}
              size="small"
              variant="outlined"
              color="success"
            />
          )}
        </Typography>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <AccessTimeIcon fontSize="small" color="action" />
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Detected Frequency
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  <Chip
                    label={temporalInfo.frequency_label}
                    size="small"
                    color="success"
                  />
                </Typography>
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CalendarTodayIcon fontSize="small" color="action" />
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Training Period
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {new Date(temporalInfo.start_date).toLocaleDateString()} →{" "}
                  {new Date(temporalInfo.end_date).toLocaleDateString()}
                </Typography>
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Training Periods
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {temporalInfo.total_periods}{" "}
                {temporalInfo.frequency_label?.toLowerCase()}
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Average Interval
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {temporalInfo.average_interval}
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Explainer-specific Info */}
      {explainerName && (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            bgcolor: `${explainerInfo.color}.50`,
            border: "1px solid",
            borderColor: `${explainerInfo.color}.200`,
            borderRadius: 2,
          }}
        >
          <Typography
            variant="subtitle2"
            sx={{
              mb: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
              color: `${explainerInfo.color}.main`,
            }}
          >
            {explainerInfo.icon}
            {explainerInfo.title} Analysis
          </Typography>

          <Typography variant="body2" sx={{ mb: 1.5 }}>
            {explainerInfo.description}
          </Typography>

          {explainerInfo.details.length > 0 && (
            <>
              <Divider sx={{ my: 1.5 }} />
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mb: 1 }}
              >
                What you'll learn:
              </Typography>
              <Box component="ul" sx={{ m: 0, pl: 2 }}>
                {explainerInfo.details.map((detail, index) => (
                  <Typography
                    key={index}
                    component="li"
                    variant="body2"
                    color="text.secondary"
                  >
                    {detail}
                  </Typography>
                ))}
              </Box>
            </>
          )}

          {horizon && (
            <Alert severity="info" sx={{ mt: 2 }} icon={<AccessTimeIcon />}>
              <Typography variant="body2">
                <strong>Forecast Window:</strong> The explainer will analyze{" "}
                <strong>{horizon}</strong>{" "}
                {temporalInfo.frequency_label?.toLowerCase() || "periods"} into
                the future, from{" "}
                <strong>
                  {new Date(temporalInfo.end_date).toLocaleDateString()}
                </strong>{" "}
                onwards.
              </Typography>
            </Alert>
          )}
        </Paper>
      )}
    </Box>
  );
}

ForecastingExplainerInfo.propTypes = {
  temporalInfo: PropTypes.shape({
    frequency_label: PropTypes.string,
    frequency_code: PropTypes.string,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    total_periods: PropTypes.number,
    average_interval: PropTypes.string,
    frequency_example: PropTypes.string,
    timestamp_column: PropTypes.string,
  }),
  loading: PropTypes.bool,
  explainerName: PropTypes.string,
  modelName: PropTypes.string,
  horizon: PropTypes.number,
};

ForecastingExplainerInfo.defaultProps = {
  temporalInfo: null,
  loading: false,
  explainerName: null,
  modelName: null,
  horizon: null,
};

export default ForecastingExplainerInfo;
