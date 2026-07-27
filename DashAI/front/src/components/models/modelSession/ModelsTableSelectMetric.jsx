import { MenuItem, TextField } from "@mui/material";
import React, { useEffect, useState } from "react";
import useMetricsByTask from "../../../hooks/useMetricByTask";

function ModelsTableSelectMetric({
  taskName,
  metricName,
  handleSelectedMetric,
  required = false,
  variant = "outlined",
}) {
  const { compatibleMetrics, loading } = useMetricsByTask({ taskName });
  const [selectedMetric, setSelectedMetric] = useState(metricName);

  // Every other field in this form (optimizer, its parameters) starts out
  // with a default value — the goal metric was the one exception, left
  // empty until the user picked one. Default to the first compatible metric
  // once the list loads, same as the rest.
  useEffect(() => {
    if (!selectedMetric && !loading && compatibleMetrics.length > 0) {
      const defaultMetric = compatibleMetrics[0].name;
      setSelectedMetric(defaultMetric);
      handleSelectedMetric(defaultMetric);
    }
  }, [selectedMetric, loading, compatibleMetrics, handleSelectedMetric]);

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
      // A non-empty list with nothing selected is only ever the one render
      // between the list loading and the auto-select effect above filling it
      // in — never a state the user can actually leave sitting empty — so it
      // isn't a real error. Only an empty list (no compatible metric to
      // default to) is worth flagging.
      error={
        required &&
        !selectedMetric &&
        !loading &&
        compatibleMetrics.length === 0
      }
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
