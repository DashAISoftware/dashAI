import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  Chip,
  DialogContent,
  Grid,
  MenuItem,
  TextField,
  Typography,
} from "@mui/material";
import { getComponents as getComponentsRequest } from "../../../api/component";
import { validateNode } from "../../../api/pipeline";
import { useSnackbar } from "notistack";

const MetricsEvalNode = ({ open, onClose, onSave, savedConfig, prevNodes }) => {
  const [metrics, setMetrics] = useState(savedConfig?.metrics || []);
  const [availableMetrics, setAvailableMetrics] = useState([]);
  const { enqueueSnackbar } = useSnackbar();

  const taskNode = prevNodes?.find((node) => node?.task);
  const task = taskNode?.task || "";

  useEffect(() => {
    setMetrics(savedConfig?.metrics || []);
  }, [savedConfig]);

  useEffect(() => {
    const fetchMetrics = async () => {
      if (!task) {
        setAvailableMetrics([]);
        return;
      }

      try {
        const metricsList = await getComponentsRequest({
          selectTypes: ["Metric"],
          relatedComponent: task,
        });
        setAvailableMetrics(metricsList);
      } catch (error) {
        console.error("Error fetching metrics:", error);
      }
    };

    fetchMetrics();
  }, [task]);

  const handleSave = async () => {
    const payload = { metrics };

    try {
      const response = await validateNode("MetricsEval", payload);
      if (response.status === "ok") {
        onSave(payload);
        onClose();
      } else {
        enqueueSnackbar(response.message || "Validation failed", {
          variant: "error",
        });
      }
    } catch (e) {
      enqueueSnackbar("Error validating node", { variant: "error" });
      console.error(e);
    }
  };

  return (
    <DialogContent
      sx={{
        width: { xs: "100%", md: 760 },
        maxWidth: "100%",
      }}
    >
      <Grid container spacing={2} direction="column">
        <Grid item xs={12}>
          <Typography variant="body1" sx={{ fontWeight: 600 }}>
            Metric Evaluation
          </Typography>
        </Grid>
        <Grid item xs={12}>
          <Box sx={{ width: "100%", maxWidth: "calc(100% - 8px)" }}>
            <TextField
              label="Metrics"
              select
              fullWidth
              value={metrics}
              onChange={(e) => setMetrics(e.target.value)}
              margin="normal"
              disabled={!task}
              slotProps={{
                select: {
                  multiple: true,
                  MenuProps: {
                    PaperProps: {
                      sx: {
                        maxHeight: 420,
                      },
                    },
                  },
                  renderValue: (selected) => (
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                      {selected.map((metricName) => (
                        <Chip
                          key={metricName}
                          label={metricName}
                          size="small"
                        />
                      ))}
                    </Box>
                  ),
                },
              }}
              sx={{
                "& .MuiInputBase-root": {
                  minHeight: 58,
                },
                "& .MuiSelect-select": {
                  minHeight: "56px",
                  display: "flex",
                  alignItems: "center",
                },
              }}
            >
              {availableMetrics.map((metric) => (
                <MenuItem key={metric.name} value={metric.name}>
                  {metric.name}
                </MenuItem>
              ))}
            </TextField>
          </Box>

          {!task && (
            <Typography variant="body2" color="warning.main" sx={{ mt: 1 }}>
              ⚠️ Connect a Task &amp; Model node first so compatible metrics can
              be listed.
            </Typography>
          )}
        </Grid>
      </Grid>

      <Box mt={3}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={handleSave}
          disabled={!task || metrics.length === 0}
        >
          Save
        </Button>
      </Box>
    </DialogContent>
  );
};

MetricsEvalNode.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  savedConfig: PropTypes.object,
  prevNodes: PropTypes.arrayOf(PropTypes.object),
};

MetricsEvalNode.defaultProps = {
  savedConfig: null,
  prevNodes: [],
};

export default MetricsEvalNode;
