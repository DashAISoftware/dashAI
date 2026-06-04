import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  IconButton,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Checkbox,
  FormControlLabel,
  Stack,
  CircularProgress,
  Alert,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { getFoldMetrics, runStatisticalTest } from "../../api/statisticalTests";

/**
 * Modal dialog for configuring and running a specific statistical test.
 * Opens when user clicks on a test in the test list.
 */
function TestModal({
  open,
  onClose,
  runs,
  session,
  testName,
  testMetadata,
  selectedMetric: initialMetric,
  selectedSplit: initialSplit,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["models", "common"]);

  // State
  const [selectedMetric, setSelectedMetric] = useState(initialMetric || "");
  const [selectedSplit, setSelectedSplit] = useState(initialSplit || "test");
  const [selectedRuns, setSelectedRuns] = useState([]);
  const [alpha, setAlpha] = useState(0.05);
  const [alternative, setAlternative] = useState("two-sided");
  const [availableMetrics, setAvailableMetrics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  // Tests that support alternative hypothesis
  const PAIRWISE_TESTS = [
    "WilcoxonSRTest",
    "PairedTTest",
    "CorrectedPairedTTest",
  ];
  const supportAlternative = PAIRWISE_TESTS.includes(testName);

  // Filter runs that have finished successfully
  const finishedRuns = useMemo(
    () => runs.filter((run) => run.status === 3),
    [runs],
  );

  // Get available metrics based on split
  useEffect(() => {
    if (finishedRuns.length > 0) {
      const metricsSet = new Set();
      finishedRuns.forEach((run) => {
        const metricsObj =
          selectedSplit === "train"
            ? run.train_metrics
            : selectedSplit === "validation"
              ? run.validation_metrics
              : run.test_metrics;

        if (metricsObj && typeof metricsObj === "object") {
          Object.keys(metricsObj).forEach((metric) => metricsSet.add(metric));
        }
      });
      const metricsList = Array.from(metricsSet).sort();
      setAvailableMetrics(metricsList);
      if (metricsList.length > 0 && !selectedMetric) {
        setSelectedMetric(metricsList[0]);
      }
    }
  }, [selectedSplit, finishedRuns, selectedMetric]);

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      setSelectedRuns([]);
      setError(null);
      setResults(null);
      setAlpha(0.05);
      setAlternative("two-sided");
    }
  }, [open]);

  const handleRunToggle = (run) => {
    setSelectedRuns((prev) =>
      prev.some((r) => r.id === run.id)
        ? prev.filter((r) => r.id !== run.id)
        : [...prev, run],
    );
  };

  const handleClose = () => {
    setSelectedRuns([]);
    setError(null);
    setResults(null);
    onClose();
  };

  const validateRunSelection = () => {
    const minRuns = testMetadata?.min_runs || 2;
    const maxRuns = testMetadata?.max_runs;

    if (selectedRuns.length < minRuns) {
      setError(
        t("models:error.minimumRunsRequired", {
          min: minRuns,
          current: selectedRuns.length,
        }) ||
          `Minimum ${minRuns} runs required, you have selected ${selectedRuns.length}`,
      );
      return false;
    }

    if (maxRuns && selectedRuns.length > maxRuns) {
      setError(
        t("models:error.maximumRunsExceeded", {
          max: maxRuns,
          current: selectedRuns.length,
        }) ||
          `Maximum ${maxRuns} runs allowed, you have selected ${selectedRuns.length}`,
      );
      return false;
    }

    if (!selectedMetric) {
      setError(t("models:error.selectMetric"));
      return false;
    }

    return true;
  };

  const handleExecuteTest = async () => {
    setError(null);

    if (!validateRunSelection()) {
      return;
    }

    setLoading(true);

    try {
      // Create mapping of run_id to run_name
      const runNames = {};
      selectedRuns.forEach((run) => {
        runNames[run.id.toString()] = run.name;
      });

      // Fetch fold metrics for selected runs
      const foldMetricsData = {};
      for (const run of selectedRuns) {
        const metrics = await getFoldMetrics(
          run.id,
          selectedSplit,
          run.nested ? "outer" : "fold",
        );
        foldMetricsData[run.id] = metrics[selectedMetric] || [];
      }

      // For Shapiro test (normality check), run separately for each run
      if (testName === "ShapiroTest") {
        const shapiroResults = [];
        for (const run of selectedRuns) {
          const response = await runStatisticalTest(
            testName,
            selectedMetric,
            selectedSplit,
            [run.id],
            { [run.id.toString()]: run.name },
            { [run.id]: foldMetricsData[run.id] },
            alpha,
          );
          shapiroResults.push({
            runId: run.id,
            runName: run.name,
            result: response,
          });
        }
        setResults({
          test_name: testName,
          shapiro_results: shapiroResults,
          all_normal: shapiroResults.every(
            (r) => r.result.significant === false,
          ),
        });
      } else {
        // For other tests, run once with all selected runs
        const testResponse = await runStatisticalTest(
          testName,
          selectedMetric,
          selectedSplit,
          selectedRuns.map((r) => r.id),
          runNames,
          foldMetricsData,
          alpha,
          supportAlternative ? { alternative } : {},
        );

        setResults(testResponse);
      }

      enqueueSnackbar(
        t("models:message.testExecutedSuccess") || "Test executed successfully",
        {
          variant: "success",
        },
      );
    } catch (err) {
      console.error("Error executing statistical test:", err);
      setError(
        err.response?.data?.detail ||
          t("models:error.failedToExecuteTest") ||
          "Failed to execute test",
      );
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { minHeight: "500px" },
      }}
    >
      <DialogTitle sx={{ bgcolor: "background.paper" }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {t(`models:test.${testName}`) || testName}
          <IconButton
            onClick={handleClose}
            size="small"
            sx={{ color: "text.secondary" }}
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {typeof error === "string"
              ? error
              : error?.msg || JSON.stringify(error)}
          </Alert>
        )}

        <Stack spacing={3}>
          {/* Metric and Split Selectors */}
          <Box sx={{ display: "flex", gap: 2 }}>
            <FormControl sx={{ flex: 1, minWidth: 200 }}>
              <InputLabel>{t("common:metric")}</InputLabel>
              <Select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                label={t("common:metric")}
                disabled={availableMetrics.length === 0}
              >
                {availableMetrics.map((metric) => (
                  <MenuItem key={metric} value={metric}>
                    {metric}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl sx={{ flex: 1, minWidth: 200 }}>
              <InputLabel>{t("common:split")}</InputLabel>
              <Select
                value={selectedSplit}
                onChange={(e) => setSelectedSplit(e.target.value)}
                label={t("common:split")}
              >
                <MenuItem value="train">{t("common:train")}</MenuItem>
                <MenuItem value="test">{t("common:test")}</MenuItem>
                {session?.splits &&
                  typeof session.splits === "object" &&
                  (session.splits.validation_split ||
                    session.splits.n_splits) && (
                    <MenuItem value="validation">
                      {t("common:validation")}
                    </MenuItem>
                  )}
              </Select>
            </FormControl>
          </Box>

          {/* Alpha Slider */}
          <Box>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
            >
              <Typography variant="body2">
                {t("models:label.significanceLevel")} (α)
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 600,
                  color: "primary.main",
                  minWidth: "50px",
                  textAlign: "right",
                }}
              >
                {alpha.toFixed(2)}
              </Typography>
            </Box>
            <Slider
              value={alpha}
              onChange={(e, newValue) => setAlpha(newValue)}
              min={0.01}
              max={0.2}
              step={0.01}
              marks={[
                { value: 0.01, label: "0.01" },
                { value: 0.1, label: "0.1" },
                { value: 0.2, label: "0.2" },
              ]}
              valueLabelDisplay="off"
              disabled={loading}
            />
          </Box>

          {/* Alternative Hypothesis - only for pairwise tests */}
          {supportAlternative && (
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>{t("models:label.alternativeHypothesis")}</InputLabel>
              <Select
                value={alternative}
                onChange={(e) => setAlternative(e.target.value)}
                label={t("models:label.alternativeHypothesis")}
              >
                <MenuItem value="two-sided">
                  {t("models:alternative.twoSided")}
                </MenuItem>
                <MenuItem value="greater">
                  {t("models:alternative.greater")}
                </MenuItem>
                <MenuItem value="less">{t("models:alternative.less")}</MenuItem>
              </Select>
            </FormControl>
          )}

          {/* Runs Selection */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
              {t("models:label.modelsToCompare")}
              {testMetadata && (
                <Typography
                  variant="caption"
                  sx={{ ml: 1, color: "text.secondary" }}
                >
                  ({t("models:label.required")}: {testMetadata.min_runs}
                  {testMetadata.max_runs &&
                  testMetadata.max_runs !== testMetadata.min_runs
                    ? `-${testMetadata.max_runs}`
                    : ""}
                  )
                </Typography>
              )}
            </Typography>

            {finishedRuns.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                {t("models:label.noFinishedRuns")}
              </Typography>
            ) : (
              <Stack spacing={1} sx={{ pl: 1 }}>
                {finishedRuns.map((run) => (
                  <FormControlLabel
                    key={run.id}
                    control={
                      <Checkbox
                        checked={selectedRuns.some((r) => r.id === run.id)}
                        onChange={() => handleRunToggle(run)}
                        disabled={loading}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">{run.name}</Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: "block", mt: 0.25 }}
                        >
                          {new Date(run.created).toLocaleDateString()}
                        </Typography>
                      </Box>
                    }
                  />
                ))}
              </Stack>
            )}
          </Box>
        </Stack>

        {/* Results Display */}
        {results && (
          <Box
            sx={{
              mt: 3,
              pt: 2,
              borderTop: "1px solid",
              borderColor: "divider",
            }}
          >
            <Typography variant="h6" sx={{ mb: 2 }}>
              {t("models:label.results")}
            </Typography>

            {results.shapiro_results ? (
              // Shapiro results (one per run)
              <Stack spacing={2}>
                {results.shapiro_results.map((shapeResult, idx) => (
                  <Alert
                    key={idx}
                    severity={
                      shapeResult.result.significant ? "warning" : "success"
                    }
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {shapeResult.runName}
                    </Typography>
                    <Typography variant="caption">
                      p-value: {shapeResult.result.p_value?.toFixed(4) || "N/A"}
                    </Typography>
                    <Typography variant="caption" sx={{ display: "block" }}>
                      {shapeResult.result.significant
                        ? t("models:message.normalityNotDetected")
                        : t("models:message.normalityDetected")}
                    </Typography>
                  </Alert>
                ))}
              </Stack>
            ) : (
              // Standard test results
              <Stack spacing={1}>
                <Box sx={{ display: "flex", gap: 2 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("models:label.statistic")}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {results.statistic?.toFixed(4) || "N/A"}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("models:label.pValue")}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {results.p_value && results.p_value < 0.0001
                        ? results.p_value.toExponential(2)
                        : results.p_value?.toFixed(4) || "N/A"}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("models:label.significant")}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 600,
                        color: results.significant
                          ? "success.main"
                          : "warning.main",
                      }}
                    >
                      {results.significant ? t("common:yes") : t("common:no")}
                    </Typography>
                  </Box>
                </Box>
              </Stack>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ bgcolor: "background.paper", p: 2 }}>
        <Button onClick={handleClose} disabled={loading}>
          {t("common:cancel")}
        </Button>
        <Button
          variant="contained"
          onClick={handleExecuteTest}
          disabled={
            loading || finishedRuns.length === 0 || selectedRuns.length === 0
          }
        >
          {loading ? (
            <>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              {t("common:executing")}
            </>
          ) : (
            t("common:execute")
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

TestModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  runs: PropTypes.arrayOf(PropTypes.object).isRequired,
  session: PropTypes.object.isRequired,
  testName: PropTypes.string.isRequired,
  testMetadata: PropTypes.object,
  selectedMetric: PropTypes.string,
  selectedSplit: PropTypes.string,
};

export default TestModal;
