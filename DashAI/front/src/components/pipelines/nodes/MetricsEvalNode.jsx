import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  DialogContent,
  Typography,
  TextField,
  MenuItem,
  Grid,
} from "@mui/material";
import { getComponents as getComponentsRequest } from "../../../api/component";
import { validateNode } from "../../../api/pipeline";
import { useSnackbar } from "notistack";

/**
 * MetricsEvalNode – selects metrics to evaluate the trained model.
 *
 * Expects a TaskAndModel upstream node (via prevNodes) so it can filter
 * compatible metrics by the selected task.
 */
const MetricsEvalNode = ({ open, onClose, onSave, savedConfig, prevNodes }) => {
  const [metrics, setMetrics] = useState(savedConfig?.metrics || []);
  const [availableMetrics, setAvailableMetrics] = useState([]);
  const { enqueueSnackbar } = useSnackbar();

  // Locate the task from an upstream TaskAndModel (or Train) node
  const taskNode = prevNodes?.find((node) => node?.task);
  const task = taskNode?.task || "";

  // ---------- Fetch compatible metrics ----------
  useEffect(() => {
    const fetchMetrics = async () => {
      if (!task) return;
      try {
        const metricsResult = await getComponentsRequest({
          selectTypes: ["Metric"],
          relatedComponent: task,
        });
        setAvailableMetrics(metricsResult);
      } catch (error) {
        console.error("Error fetching metrics:", error);
      }
    };
    fetchMetrics();
  }, [task]);

  // Restore saved selection
  useEffect(() => {
    if (savedConfig?.metrics) {
      setMetrics(savedConfig.metrics);
    }
  }, [savedConfig]);

  // ---------- Save ----------
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
    <DialogContent>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Typography variant="body1" sx={{ fontWeight: 600 }}>
            Metric Evaluation
          </Typography>
          {!task && (
            <Typography variant="body2" color="warning.main" sx={{ mt: 1 }}>
              ⚠️ Connect a Task &amp; Model node first so compatible metrics
              can be listed.
            </Typography>
          )}
        </Grid>

        <Grid item xs={12}>
          <TextField
            label="Metrics"
            select
            fullWidth
            value={metrics}
            onChange={(e) => setMetrics(e.target.value)}
            margin="normal"
            disabled={!task}
            slotProps={{ select: { multiple: true } }}
          >
            {availableMetrics.map((metric) => (
              <MenuItem key={metric.name} value={metric.name}>
                {metric.name}
              </MenuItem>
            ))}
          </TextField>
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
