import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Button,
  Container,
  Stack,
  CircularProgress,
  Alert,
} from "@mui/material";
import { getComponents } from "../../../api/component";
import SplitColumn from "./SplitColumn";

export default function MetricsSelector({
  experiment,
  setExperiment,
  setNextEnabled,
}) {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);

  const enabledSplits = {
    train: !!experiment.splits?.train,
    validation: !!experiment.splits?.validation,
    test: !!experiment.splits?.test,
  };

  const missingSplits = Object.entries(enabledSplits)
    .filter(
      ([split, enabled]) =>
        enabled && experiment[`${split}_metrics`].length === 0
    )
  .map(([split]) => split);

  useEffect(() => {
    const fetchMetrics = async () => {
      setLoading(true);
      try {
        const data = await getComponents({
          selectTypes: ["Metric"],
          relatedComponent: experiment.task_name,
        });
        setMetrics(data);
      } catch (error) {
        console.error("Error fetching metrics:", error);
      } finally {
        setLoading(false);
      }
    };

    if (experiment.task_name) {
      fetchMetrics();
    }
  }, [experiment.task_name]);

  useEffect(() => {
    const isValid = Object.entries(enabledSplits).every(
      ([split, enabled]) => {
        if (!enabled) return true; // ignore disabled split
        return experiment[`${split}_metrics`].length > 0;
      }
    );

    setNextEnabled(isValid);
  }, [
    enabledSplits,
    experiment.train_metrics,
    experiment.validation_metrics,
    experiment.test_metrics,
    setNextEnabled,
  ]);

  const toggleMetric = (split, name) => {
    const key = `${split}_metrics`;

    setExperiment(prev => {
      const current = prev[key];
      const updated = current.includes(name)
        ? current.filter(m => m !== name)
        : [...current, name];

      return {
        ...prev,
        [key]: updated,
      };
    });
  };

  const selectAllForSplit = split => {
    const key = `${split}_metrics`;

    setExperiment(prev => ({
      ...prev,
      [key]: metrics.map(m => m.name),
    }));
  };

  if (loading) {
    return (
      <Box
        minHeight="60vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box minHeight="100%">
      <Typography
        variant="h6"
        gutterBottom
        sx={{ display: "flex", alignItems: "center", gap: 1 }}
      >
        Select Metrics for Each Data Split
      </Typography>

      <Typography variant="body2" color="text.secondary" gutterBottom>
        Choose which metrics to compute for the training, test, and validation
        sets.
      </Typography>

      <Container sx={{ py: 4 }}>
        {/* Quick actions */}
        <Stack
          direction="row"
          spacing={2}
          justifyContent="center"
          mb={4}
          alignItems="center"
        >
          <Typography variant="body2" color="text.secondary">
            Quick select all:
          </Typography>
          <Button onClick={() => selectAllForSplit("train")} variant="contained">
            Train
          </Button>
          <Button
            onClick={() => selectAllForSplit("validation")}
            variant="contained"
          >
            Validation
          </Button>
          <Button onClick={() => selectAllForSplit("test")} variant="contained">
            Test
          </Button>
          
        </Stack>

        {/* Columns */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
            gap: 3,
          }}
        >
          <SplitColumn
            title="Training Set"
            splitType="train"
            metrics={metrics}
            selectedMetrics={experiment.train_metrics}
            onToggleMetric={name => toggleMetric("train", name)}
            disabled={!experiment.splits?.train}
          />

          <SplitColumn
            title="Validation Set"
            splitType="validation"
            metrics={metrics}
            selectedMetrics={experiment.validation_metrics}
            onToggleMetric={name => toggleMetric("validation", name)}
            disabled={!experiment.splits?.validation}
          />

          <SplitColumn
            title="Test Set"
            splitType="test"
            metrics={metrics}
            selectedMetrics={experiment.test_metrics}
            onToggleMetric={name => toggleMetric("test", name)}
            disabled={!experiment.splits?.test}
          />
        </Box>

        {/* Alert */}
        {missingSplits.length > 0 && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            {missingSplits.length === 1 ? (
              <>
                {missingSplits[0].charAt(0).toUpperCase() + missingSplits[0].slice(1)} split must have at least one metric selected.
              </>
            ) : (
              <>
                The following splits must have at least one metric selected:{" "}
                {missingSplits.map((split, idx) => (
                  <span key={split}>
                    <strong>{split.charAt(0).toUpperCase() + split.slice(1)}</strong>
                    {idx < missingSplits.length - 1 ? ", " : ""}
                  </span>
                ))}
              </>
            )}
          </Alert>
        )}
      </Container>
    </Box>
  );
}
