import { MenuItem, TextField } from "@mui/material";
import React, { useState } from "react";
import useMetricsByTask from "../../../hooks/useMetricByTask";

function ModelsTableSelectMetric({
  taskName,
  metricName,
  handleSelectedMetric,
  required = false,
  variant = "outlined",
}) {
  const { compatibleMetrics } = useMetricsByTask({ taskName });
  const [selectedMetric, setSelectedMetric] = useState(metricName);

  const handleChange = (e) => {
    const goalMetric = e.target.value;
    setSelectedMetric(goalMetric);
    handleSelectedMetric(goalMetric);
  };

  return (
    <TextField
      select
      value={selectedMetric || ""}
      onChange={handleChange}
      size="small"
      variant={variant}
      fullWidth
      required={required}
      error={required && !selectedMetric}
      slotProps={{
        MenuProps: {
          PaperProps: {
            style: {
              maxHeight: 300,
            },
          },
        },
      }}
    >
      {compatibleMetrics.map((metric) => (
        <MenuItem key={metric.name} value={metric.name}>
          {metric.name}
        </MenuItem>
      ))}
    </TextField>
  );
}

export default ModelsTableSelectMetric;
