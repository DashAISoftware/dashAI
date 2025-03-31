import { MenuItem, TextField } from "@mui/material";
import React, { useState } from "react";
import useMetricsByTask from "../../hooks/useMetricByTask";

function ModelsTableSelectMetric({
  taskName,
  metricName,
  handleSelectedMetric,
}) {
  const { compatibleMetrics } = useMetricsByTask({ taskName });
  const [selectedMetric, setSelectedMetric] = useState(metricName);

  const handleChange = (e) => {
    const goalMetric = e.target.value;
    setSelectedMetric(goalMetric);
    handleSelectedMetric(goalMetric);
  };

  return (
    <>
      <TextField
        select
        label="Goal metric for optimization"
        value={selectedMetric || ""}
        onChange={handleChange}
        fullWidth
      >
        {compatibleMetrics.map((metric) => (
          <MenuItem key={metric.name} value={metric.name}>
            {metric.name}
          </MenuItem>
        ))}
      </TextField>
    </>
  );
}

export default ModelsTableSelectMetric;
