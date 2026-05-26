import { useState, useEffect, useRef, useCallback, useMemo } from "react";
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
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Collapse,
  IconButton,
} from "@mui/material";
import { ExpandMore, ExpandLess, Help } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import {
  getFoldMetrics,
  checkNormality,
  runStatisticalTest,
} from "../../api/statisticalTests";
import { getHypothesisDecisionMessage } from "../../utils/translateHypothesisDecision";

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
  const [showDetails, setShowDetails] = useState(false);
  const [alternative, setAlternative] = useState("two-sided");

  // Tests that support alternative hypothesis
  const PAIRWISE_TESTS = [
    "WilcoxonSRTest",
    "PairedTTest",
    "CorrectedPairedTTest",
  ];
  const supportAlternative = PAIRWISE_TESTS.includes(selectedTest);
  const { t } = useTranslation(["models", "common"]);
  const [panelHeight, setPanelHeight] = useState(400);
  const isResizing = useRef(false);

  const postHocTestLabels = {
    FriedmanTest: "models:label.nemenyiPairwiseComparisons",
    AnovaTest: "models:label.tukeyPairwiseComparisons",
    PairwiseWilcoxonTest: "models:label.wilcoxonPairwiseComparisons",
  };

  const formatPValue = (p) => {
    if (p < 0.0001) return p.toExponential(2);
    return p.toFixed(4);
  };

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
  const finishedRuns = useMemo(
    () => runs.filter((run) => run.status === 3),
    [runs],
  );

  const runIds = useMemo(
    () => selectedRuns.map((run) => run.id),
    [selectedRuns],
  );

  // Determine available tests based on number of selected runs
  const availableTests = useMemo(() => {
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

  const handleRunToggle = (run) => {
    setSelectedRuns((prev) =>
      prev.some((r) => r.id === run.id)
        ? prev.filter((r) => r.id !== run.id)
        : [...prev, run],
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
      // Create mapping of run_id to run_name from selected runs
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

      const normalityResponse = await checkNormality(
        selectedMetric,
        selectedSplit,
        runIds,
        runNames,
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
      // Create mapping of run_id to run_name from selected runs
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

      // Execute the statistical test via service
      const testResponse = await runStatisticalTest(
        selectedTest,
        selectedMetric,
        selectedSplit,
        runIds,
        runNames,
        foldMetricsData,
        alpha,
        supportAlternative ? { alternative } : {},
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
        }}
      >
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {typeof error === "string"
              ? error
              : error?.msg || JSON.stringify(error)}
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
                  {finishedRuns.map((run) => {
                    const isSelected = selectedRuns.some(
                      (r) => r.id === run.id,
                    );
                    const selIdx = selectedRuns.findIndex(
                      (r) => r.id === run.id,
                    );
                    return (
                      <FormControlLabel
                        key={run.id}
                        control={
                          <Checkbox
                            checked={isSelected}
                            onChange={() => handleRunToggle(run)}
                          />
                        }
                        label={
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 0.75,
                            }}
                          >
                            <Box>
                              <Typography variant="body2">
                                {run.name}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{ display: "block", mt: 0.25 }}
                              >
                                {new Date(run.created).toLocaleDateString()}
                              </Typography>
                            </Box>
                            {selIdx === 0 && (
                              <Chip
                                label={t("models:label.model1")}
                                size="small"
                                color="primary"
                                variant="outlined"
                                sx={{ fontSize: "0.65rem", height: 18 }}
                              />
                            )}
                            {selIdx === 1 && (
                              <Chip
                                label={t("models:label.model2")}
                                size="small"
                                color="secondary"
                                variant="outlined"
                                sx={{ fontSize: "0.65rem", height: 18 }}
                              />
                            )}
                          </Box>
                        }
                      />
                    );
                  })}
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
              {/* Help icon + Button row */}
              <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                <Tooltip
                  title={t("models:message.normalityCheckTooltip")}
                  arrow
                >
                  <Help
                    sx={{
                      fontSize: "1.2rem",
                      color: "text.secondary",
                      cursor: "help",
                      flexShrink: 0,
                    }}
                  />
                </Tooltip>

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
              </Box>

              {/* Normality Result */}
              {normalityResult && (
                <Box>
                  <Alert
                    severity={normalityResult.is_normal ? "success" : "warning"}
                    sx={{ fontSize: "0.875rem", mb: 1.5 }}
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

                  {/* Show test method and individual p-values */}
                  <Box
                    sx={{
                      bgcolor: "action.hover",
                      p: 1.5,
                      borderRadius: 1,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{ fontWeight: 600, display: "block", mb: 1 }}
                      color="text.secondary"
                    >
                      {t("models:message.normalityCheckMethod")}
                    </Typography>

                    {/* Individual run p-values */}
                    {normalityResult.results_by_run &&
                      normalityResult.results_by_run.length > 0 && (
                        <Box sx={{ mt: 1 }}>
                          {normalityResult.results_by_run.map((result, idx) => {
                            const runName =
                              finishedRuns.find((r) => r.id === result.run_id)
                                ?.name || `Run ${result.run_id}`;
                            return (
                              <Box
                                key={idx}
                                sx={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  py: 0.5,
                                  fontSize: "0.8rem",
                                  borderBottom:
                                    idx <
                                    normalityResult.results_by_run.length - 1
                                      ? "1px solid"
                                      : "none",
                                  borderColor: "divider",
                                }}
                              >
                                <Typography variant="caption">
                                  {runName}
                                </Typography>
                                <Box sx={{ display: "flex", gap: 2, ml: 1 }}>
                                  <Typography
                                    variant="caption"
                                    sx={{
                                      color: result.is_normal
                                        ? "success.main"
                                        : "warning.main",
                                      fontWeight: 600,
                                    }}
                                  >
                                    p = {result.p_value.toFixed(4)}
                                  </Typography>
                                  <Chip
                                    label={
                                      result.is_normal ? "Normal" : "Non-normal"
                                    }
                                    size="small"
                                    color={
                                      result.is_normal ? "success" : "warning"
                                    }
                                    variant="outlined"
                                  />
                                </Box>
                              </Box>
                            );
                          })}
                        </Box>
                      )}
                  </Box>
                </Box>
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

          {/* Alternative hypothesis selector - only for pairwise tests */}
          {supportAlternative && (
            <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
              <Box
                sx={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  gap: 0.5,
                }}
              >
                <FormControl sx={{ minWidth: 0 }} size="small">
                  <InputLabel>
                    {t("models:label.alternativeHypothesis")}
                  </InputLabel>
                  <Select
                    value={alternative}
                    onChange={(e) => setAlternative(e.target.value)}
                    label={t("models:label.alternativeHypothesis")}
                    MenuProps={{
                      disablePortal: false,
                      style: { zIndex: 9999 },
                    }}
                  >
                    <MenuItem value="two-sided">
                      {t("models:alternative.twoSided")}
                    </MenuItem>
                    <MenuItem value="greater">
                      {t("models:alternative.greater")}
                    </MenuItem>
                    <MenuItem value="less">
                      {t("models:alternative.less")}
                    </MenuItem>
                  </Select>
                </FormControl>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: 0.5, display: "block" }}
                >
                  {selectedRuns.length === 2 &&
                    (() => {
                      const m1 = selectedRuns[0];
                      const m2 = selectedRuns[1];
                      return m1 && m2 ? (
                        <>
                          {t("models:label.model1")}: <strong>{m1.name}</strong>
                          <br />
                          {t("models:label.model2")}: <strong>{m2.name}</strong>
                        </>
                      ) : null;
                    })()}
                </Typography>
              </Box>
              <Box sx={{ flex: 1 }} />
            </Box>
          )}
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
            {/* Header: test name + significance badge */}
            <Box
              sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}
            >
              <Typography variant="h6">{results.test_name}</Typography>
              <Chip
                label={
                  results.significant
                    ? t("models:label.significant")
                    : t("models:label.notSignificant")
                }
                color={results.significant ? "success" : "default"}
                size="small"
              />
            </Box>

            {/* Key stats */}
            <Box
              sx={{
                display: "flex",
                gap: 3,
                mb: 2,
                p: 1.5,
                bgcolor: "action.hover",
                borderRadius: 1,
              }}
            >
              {results.statistic !== null && !isNaN(results.statistic) && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t("models:label.statistic")}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {results.statistic?.toFixed(4)}
                  </Typography>
                </Box>
              )}
              {results.p_value !== null && !isNaN(results.p_value) && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    p-value
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: results.significant
                        ? "success.main"
                        : "text.primary",
                    }}
                  >
                    {formatPValue(results.p_value)}
                  </Typography>
                </Box>
              )}
              <Box>
                <Typography variant="caption" color="text.secondary">
                  α
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {results.alpha}
                </Typography>
              </Box>
            </Box>

            {/* Interpretation */}
            {results.p_value !== null && !isNaN(results.p_value) && (
              <Alert
                severity={results.significant ? "success" : "info"}
                sx={{ mb: 2 }}
              >
                {getHypothesisDecisionMessage(
                  results.significant,
                  formatPValue(results.p_value),
                  results.alpha,
                  t,
                )}
              </Alert>
            )}

            {/* Post-hoc pairwise table */}
            {results.posthoc && results.posthoc.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  {t(
                    postHocTestLabels[results.test_name] ||
                      "models:label.pairwiseComparisons",
                  )}
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("models:label.model1")}</TableCell>
                      <TableCell>{t("models:label.model2")}</TableCell>
                      <TableCell align="right">p-value</TableCell>
                      <TableCell align="center">
                        {t("models:label.result")}
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {results.posthoc.map((pair, i) => (
                      <TableRow key={i}>
                        <TableCell>{pair.run_1_name || pair.run_1}</TableCell>
                        <TableCell>{pair.run_2_name || pair.run_2}</TableCell>
                        <TableCell align="right">
                          {formatPValue(pair.p_value)}
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={
                              pair.significant
                                ? t("models:label.significant")
                                : t("models:label.notSignificant")
                            }
                            color={pair.significant ? "success" : "default"}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            )}

            {/* Technical details collapsible */}
            <Box>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  cursor: "pointer",
                  color: "text.secondary",
                }}
                onClick={() => setShowDetails((v) => !v)}
              >
                <IconButton size="small">
                  {showDetails ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
                <Typography variant="caption">
                  {t("models:label.technicalDetails")}
                </Typography>
              </Box>
              <Collapse in={showDetails}>
                <Box
                  sx={{
                    bgcolor: "background.paper",
                    p: 1.5,
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "divider",
                    fontFamily: "monospace",
                    fontSize: "0.75rem",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    maxHeight: 200,
                    overflow: "auto",
                    mt: 1,
                  }}
                >
                  {JSON.stringify(results.details, null, 2)}
                </Box>
              </Collapse>
            </Box>
          </Box>
        )}
      </AccordionDetails>
      <Box
        onMouseDown={() => {
          isResizing.current = true;
          document.body.style.cursor = "row-resize";
          document.body.style.userSelect = "none";
        }}
        sx={{
          height: "5px",
          cursor: "row-resize",
          bgcolor: "transparent",
          transition: "background-color 0.2s ease",
          "&:hover": { bgcolor: "primary.main" },
          zIndex: 10,
        }}
      />
    </Accordion>
  );
}
