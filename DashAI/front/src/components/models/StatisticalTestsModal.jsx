import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Button,
  Checkbox,
  FormControlLabel,
  Stack,
  CircularProgress,
  Alert,
  Divider,
} from "@mui/material";
import { ExpandMore } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import {
  getFoldMetrics,
  checkNormality,
  runStatisticalTest,
} from "../../api/statisticalTests";

export default function StatisticalTestsModal({
  runs,
  session,
  visible = false,
}) {
  const [collapsed, setCollapsed] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState("");
  const [selectedSplit, setSelectedSplit] = useState("test");
  const [selectedRuns, setSelectedRuns] = useState([]);
  const [selectedTest, setSelectedTest] = useState("");
  const [alpha, setAlpha] = useState(0.05);
  const [availableMetrics, setAvailableMetrics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [normalityCheckLoading, setNormalityCheckLoading] = useState(false);
  const [normalityResult, setNormalityResult] = useState(null);
  const { t } = useTranslation(["models", "common"]);
  const [panelHeight, setPanelHeight] = useState(400);
  const isResizing = useRef(false);

  const handleMouseMove = useCallback((e) => {
    if (!isResizing.current) return;
    const panel = document.querySelector("[data-statistical-tests-panel]");
    if (panel) {
      const rect = panel.getBoundingClientRect();
      const newHeight = e.clientY - rect.top;
      const clamped = Math.max(
        200,
        Math.min(window.innerHeight * 0.7, newHeight),
      );
      setPanelHeight(clamped);
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    isResizing.current = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // Filter runs that have finished successfully
  const finishedRuns = React.useMemo(
    () => runs.filter((run) => run.status === 3),
    [runs],
  );

  // Determine available tests based on number of selected runs
  const availableTests = React.useMemo(() => {
    if (selectedRuns.length === 2) {
      return [
        { value: "PairedTTest", label: "pairedTTest" },
        { value: "CorrectedPairedTTest", label: "correctedPairedTTest" },
        { value: "WilcoxonSRTest", label: "wilcoxonSignedRankTest" },
      ];
    } else if (selectedRuns.length >= 3) {
      return [
        { value: "AnovaTest", label: "anovaTest" },
        { value: "FriedmanTest", label: "friedmanTest" },
        { value: "PairwiseWilcoxonTest", label: "pairwiseWilcoxonTest" },
      ];
    }
    return [];
  }, [selectedRuns.length]);

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

  // Reset form when component becomes visible
  useEffect(() => {
    if (!visible) {
      setSelectedRuns([]);
      setError(null);
      setResults(null);
    }
  }, [visible]);

  // Reset selected test if it's no longer available
  useEffect(() => {
    if (selectedTest && !availableTests.some((t) => t.value === selectedTest)) {
      setSelectedTest("");
    }
  }, [availableTests, selectedTest]);

  const handleRunToggle = (runId) => {
    setSelectedRuns((prev) =>
      prev.includes(runId)
        ? prev.filter((id) => id !== runId)
        : [...prev, runId],
    );
  };

  const handleNormalityCheck = async () => {
    if (selectedRuns.length === 0 || !selectedMetric) {
      setError(t("models:error.selectRunsAndMetric"));
      return;
    }

    setNormalityCheckLoading(true);
    setError(null);
    setNormalityResult(null);

    try {
      // Fetch fold metrics for selected runs
      const foldMetricsData = {};
      for (const runId of selectedRuns) {
        const metrics = await getFoldMetrics(runId, selectedSplit);
        foldMetricsData[runId] = metrics[selectedMetric] || [];
      }

      // Check normality via service
      const normalityResponse = await checkNormality(
        selectedMetric,
        selectedSplit,
        selectedRuns,
        foldMetricsData,
      );

      setNormalityResult(normalityResponse);
    } catch (err) {
      console.error("Error checking normality:", err);
      setError(
        err.response?.data?.detail || t("models:error.failedToCheckNormality"),
      );
    } finally {
      setNormalityCheckLoading(false);
    }
  };

  const handleExecuteTest = async () => {
    if (selectedRuns.length < 2) {
      setError(t("models:error.selectAtLeastTwoRuns"));
      return;
    }

    if (!selectedMetric) {
      setError(t("models:error.selectMetric"));
      return;
    }

    if (!selectedTest) {
      setError(t("models:error.selectTest"));
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      // Fetch fold metrics for selected runs
      const foldMetricsData = {};
      for (const runId of selectedRuns) {
        const metrics = await getFoldMetrics(runId, selectedSplit);
        foldMetricsData[runId] = metrics[selectedMetric] || [];
      }

      // Execute the statistical test via service
      const testResponse = await runStatisticalTest(
        selectedTest,
        selectedMetric,
        selectedSplit,
        selectedRuns,
        foldMetricsData,
        alpha,
      );

      setResults(testResponse);
      setError(null);
    } catch (err) {
      console.error("Error executing statistical test:", err);
      setError(
        err.response?.data?.detail || t("models:error.failedToExecuteTest"),
      );
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  if (!visible) {
    return null;
  }

  return (
    <Accordion
      expanded={!collapsed}
      onChange={() => setCollapsed((v) => !v)}
      disableGutters
      elevation={1}
      sx={{
        flexShrink: 0,
        borderBottom: "1px solid",
        borderColor: "divider",
        borderRadius: "4px",
        "&:before": { display: "none" },
      }}
    >
      <AccordionSummary
        expandIcon={
          <Tooltip
            title={collapsed ? t("common:expand") : t("common:collapse")}
          >
            <ExpandMore />
          </Tooltip>
        }
        sx={{
          "& .MuiAccordionSummary-content": { my: "8px", mr: 1 },
        }}
      >
        <Typography variant="h6" color="text.primary">
          {t("models:label.statisticalTests")}
        </Typography>
      </AccordionSummary>

      <AccordionDetails
        data-statistical-tests-panel
        sx={{
          p: 2,
          overflowY: "auto",
          overflowX: "hidden",
          height: `${panelHeight}px`,
          position: "relative",
        }}
      >
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Metric and Split Selectors */}
        <Stack spacing={2} sx={{ mb: 3 }}>
          <Box sx={{ display: "flex", gap: 2 }}>
            {/* Metric Selector */}
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

            {/* Split Selector */}
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
        </Stack>

        <Divider sx={{ my: 2 }} />

        {/* Models to Compare Section */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
            {t("models:label.modelsToCompare")}
          </Typography>
          <Box sx={{ display: "flex", gap: 2 }}>
            {/* Left side - Models list (50% width) */}
            <Box sx={{ flex: 1 }}>
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
                          checked={selectedRuns.includes(run.id)}
                          onChange={() => handleRunToggle(run.id)}
                        />
                      }
                      label={
                        <Box>
                          <Typography variant="body2">
                            {run.run_name}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: "block", mt: 0.25 }}
                          >
                            {run.model_name} •{" "}
                            {new Date(run.created).toLocaleDateString()}
                          </Typography>
                        </Box>
                      }
                    />
                  ))}
                </Stack>
              )}
            </Box>

            {/* Right side - Normality check button and result (50% width) */}
            <Box
              sx={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                gap: 1.5,
              }}
            >
              <Button
                variant="outlined"
                onClick={handleNormalityCheck}
                disabled={
                  normalityCheckLoading ||
                  selectedRuns.length === 0 ||
                  !selectedMetric
                }
                fullWidth
                sx={{ textTransform: "none" }}
              >
                {normalityCheckLoading ? (
                  <>
                    <CircularProgress size={18} sx={{ mr: 1 }} />
                    {t("models:button.checkingNormality")}
                  </>
                ) : (
                  t("models:button.checkNormality")
                )}
              </Button>

              {/* Normality Result */}
              {normalityResult && (
                <Alert
                  severity={normalityResult.is_normal ? "success" : "warning"}
                  sx={{ fontSize: "0.875rem" }}
                >
                  {normalityResult.is_normal ? (
                    <Box>
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 600, mb: 0.5 }}
                      >
                        {t("models:message.normalityDetected")}
                      </Typography>
                      <Typography variant="caption">
                        {t("models:message.recommendParametricTests")}
                      </Typography>
                    </Box>
                  ) : (
                    <Box>
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 600, mb: 0.5 }}
                      >
                        {t("models:message.normalityNotDetected")}
                      </Typography>
                      <Typography variant="caption">
                        {t("models:message.recommendNonParametricTests")}
                      </Typography>
                    </Box>
                  )}
                </Alert>
              )}
            </Box>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Test Selection and Alpha */}
        <Stack spacing={3}>
          <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
            {/* Test Type Selector */}
            <FormControl
              sx={{ flex: 1, minWidth: 0 }}
              disabled={availableTests.length === 0}
            >
              <InputLabel>{t("models:label.statisticalTest")}</InputLabel>
              <Select
                value={selectedTest}
                onChange={(e) => setSelectedTest(e.target.value)}
                label={t("models:label.statisticalTest")}
              >
                {availableTests.map((test) => (
                  <MenuItem key={test.value} value={test.value}>
                    {t(`models:test.${test.label}`)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Alpha Range Slider */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
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
          </Box>

          {/* Execute Button */}
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
            <Button
              variant="contained"
              onClick={handleExecuteTest}
              disabled={
                loading || finishedRuns.length < 2 || selectedRuns.length < 2
              }
              sx={{ minWidth: 140 }}
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
            <Box
              sx={{
                bgcolor: "background.paper",
                p: 2,
                borderRadius: 1,
                border: "1px solid",
                borderColor: "divider",
                fontFamily: "monospace",
                fontSize: "0.875rem",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                maxHeight: 300,
                overflow: "auto",
              }}
            >
              {typeof results === "string"
                ? results
                : JSON.stringify(results, null, 2)}
            </Box>
          </Box>
        )}
        {/* Resize Handle */}
        <Box
          onMouseDown={() => {
            isResizing.current = true;
            document.body.style.cursor = "row-resize";
            document.body.style.userSelect = "none";
          }}
          sx={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: "5px",
            cursor: "row-resize",
            bgcolor: "transparent",
            transition: "background-color 0.2s ease",
            "&:hover": { bgcolor: "primary.main" },
            zIndex: 10,
          }}
        />
      </AccordionDetails>
    </Accordion>
  );
}
