import React, { useState, useEffect } from "react";
import { Box, Button, DialogContent, Typography, Checkbox, FormControlLabel, FormGroup } from "@mui/material";

const MetricsNode = ({ open, onClose, taskType, onSave, savedMetrics }) => {
  const [selectedMetrics, setSelectedMetrics] = useState(savedMetrics || []);

  const availableMetrics = {
    classification: ["accuracy", "f1", "precision", "recall"],
    regression: ["MSE (Mean Squared Error)", "MAE (Mean Absolute Error)", "R2 Score", "RMSE (Root Mean Squared Error)"],
    clustering: ["Silhouette Score", "Calinski-Harabasz Index", "Davies-Bouldin Index"],
    time_series: ["MAE", "RMSE", "MAPE (Mean Absolute Percentage Error)"],
  };

  // Actualiza el estado cuando cambia savedMetrics
  useEffect(() => {
    setSelectedMetrics(savedMetrics || []);
  }, [savedMetrics]);

  const handleMetricChange = (metric) => {
    setSelectedMetrics((prevMetrics) =>
      prevMetrics.includes(metric)
        ? prevMetrics.filter((m) => m !== metric)
        : [...prevMetrics, metric]
    );
  };

  const saveMetricsSelection = () => {
    onSave({ metrics: selectedMetrics }); // Guarda las métricas seleccionadas
    onClose(); // Cierra el diálogo
  };

  return (
    <DialogContent>
      <Typography variant="body1" gutterBottom>
        Choose the metrics to evaluate the model's performance:
      </Typography>
      <Box mt={2}>
        <FormGroup>
          {availableMetrics[taskType || "classification"].map((metric) => (
            <FormControlLabel
              key={metric}
              control={
                <Checkbox
                  checked={selectedMetrics.includes(metric)}
                  onChange={() => handleMetricChange(metric)}
                />
              }
              label={metric}
            />
          ))}
        </FormGroup>
      </Box>
      <Box mt={3}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={saveMetricsSelection}
          disabled={selectedMetrics.length === 0}
        >
          Save Metrics
        </Button>
      </Box>
    </DialogContent>
  );
};

export default MetricsNode;
