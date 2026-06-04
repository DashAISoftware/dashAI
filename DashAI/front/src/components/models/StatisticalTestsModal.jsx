import { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
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
import {
  Close as CloseIcon,
  ExpandMore,
  ExpandLess,
} from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { getFoldMetrics, runStatisticalTest } from "../../api/statisticalTests";
import { getHypothesisDecisionMessage } from "../../utils/translateHypothesisDecision";

const POSTHOC_TEST_LABELS = {
  FriedmanTest: "models:label.nemenyiPairwiseComparisons",
  AnovaTest: "models:label.tukeyPairwiseComparisons",
  PairwiseWilcoxonTest: "models:label.wilcoxonPairwiseComparisons",
};

export default function StatisticalTestsModal({
  test,
  runs = [],
  session,
  open = false,
  onClose,
}) {
  const { t } = useTranslation(["models", "common"]);

  const [selectedMetric, setSelectedMetric] = useState("");
  const [selectedSplit, setSelectedSplit] = useState("test");
  const [selectedRuns, setSelectedRuns] = useState([]);
  const [alpha, setAlpha] = useState(0.05);
  const [alternative, setAlternative] = useState("two-sided");
  const [availableMetrics, setAvailableMetrics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  // ----- Test-driven config (all from backend metadata) -----
  const minRuns = test?.metadata?.min_runs ?? 2;
  const maxRuns = test?.metadata?.max_runs ?? Infinity;
  const supportsAlternative = test?.metadata?.supports_alternative === true;
  const testIdentifier = test?.name; // registry name expected by the API
  const testTitle = test?.metadata?.name || test?.display_name || test?.name;

  const finishedRuns = useMemo(
    () => runs.filter((run) => run.status === 3),
    [runs],
  );

  const runIds = useMemo(
    () => selectedRuns.map((run) => run.id),
    [selectedRuns],
  );

  const countValid =
    selectedRuns.length >= minRuns && selectedRuns.length <= maxRuns;
  const atMax = selectedRuns.length >= maxRuns;

  const runsRequirementText = useMemo(() => {
    if (maxRuns === Infinity) {
      return t("models:label.selectAtLeastRuns", { min: minRuns });
    }
    if (minRuns === maxRuns) {
      return t("models:label.selectExactlyRuns", { count: minRuns });
    }
    return t("models:label.selectBetweenRuns", { min: minRuns, max: maxRuns });
  }, [minRuns, maxRuns, t]);

  const formatPValue = (p) => {
    if (p < 0.0001) return p.toExponential(2);
    return p.toFixed(4);
  };

  // Reset state each time the modal opens for a (possibly new) test
  useEffect(() => {
    if (open) {
      setSelectedRuns([]);
      setResults(null);
      setError(null);
      setAlternative("two-sided");
      setSelectedMetric("");
      setSelectedSplit("test");
      setShowDetails(false);
    }
  }, [open, testIdentifier]);

  // Derive available metrics from finished runs + chosen split
  useEffect(() => {
    if (finishedRuns.length > 0) {
      const metricsSet = new Set();
      finishedRuns.forEach((run) => {
        const metricsObj =
          selectedSplit === "train" ? run.train_metrics : run.test_metrics;
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

  const handleRunToggle = (run) => {
    setSelectedRuns((prev) => {
      const isSelected = prev.some((r) => r.id === run.id);
      if (isSelected) return prev.filter((r) => r.id !== run.id);
      if (prev.length >= maxRuns) return prev; // enforce max
      return [...prev, run];
    });
  };

  const handleExecuteTest = async () => {
    if (!countValid) {
      setError(runsRequirementText);
      return;
    }
    if (!selectedMetric) {
      setError(t("models:error.selectMetric"));
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const runNames = {};
      selectedRuns.forEach((run) => {
        runNames[run.id.toString()] = run.name;
      });

      const foldMetricsData = {};
      for (const run of selectedRuns) {
        const metrics = await getFoldMetrics(
          run.id,
          selectedSplit,
          run.nested ? "outer" : "fold",
        );
        foldMetricsData[run.id] = metrics[selectedMetric] || [];
      }

      const testResponse = await runStatisticalTest(
        testIdentifier,
        selectedMetric,
        selectedSplit,
        runIds,
        runNames,
        foldMetricsData,
        alpha,
        supportsAlternative ? { alternative } : {},
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

  if (!test) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{ sx: { minHeight: "500px" } }}
    >
      <DialogTitle sx={{ bgcolor: "background.paper" }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {testTitle}
          <IconButton
            onClick={onClose}
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

        {/* Metric and Split selectors */}
        <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
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

        <Divider sx={{ my: 2 }} />

        {/* Runs to compare */}
        <Box sx={{ mb: 3 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 1.5,
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {t("models:label.modelsToCompare")}
            </Typography>
            <Typography
              variant="caption"
              sx={{ color: countValid ? "success.main" : "text.secondary" }}
            >
              {selectedRuns.length} / {runsRequirementText}
            </Typography>
          </Box>

          {finishedRuns.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t("models:label.noFinishedRuns")}
            </Typography>
          ) : (
            <Stack spacing={1} sx={{ pl: 1 }}>
              {finishedRuns.map((run) => {
                const isSelected = selectedRuns.some((r) => r.id === run.id);
                const selIdx = selectedRuns.findIndex((r) => r.id === run.id);
                return (
                  <FormControlLabel
                    key={run.id}
                    control={
                      <Checkbox
                        checked={isSelected}
                        disabled={!isSelected && atMax}
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
                          <Typography variant="body2">{run.name}</Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: "block", mt: 0.25 }}
                          >
                            {new Date(run.created).toLocaleDateString()}
                          </Typography>
                        </Box>
                        {supportsAlternative && selIdx === 0 && (
                          <Chip
                            label={t("models:label.model1")}
                            size="small"
                            color="primary"
                            variant="outlined"
                            sx={{ fontSize: "0.65rem", height: 18 }}
                          />
                        )}
                        {supportsAlternative && selIdx === 1 && (
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

        <Divider sx={{ my: 2 }} />

        {/* Alpha + alternative hypothesis (single horizontal row) */}
        <Box sx={{ display: "flex", gap: 3, alignItems: "flex-start" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
            >
              <Typography variant="body2">
                {t("models:label.significanceLevel")} (α)
              </Typography>
              <Typography
                variant="body2"
                sx={{ fontWeight: 600, color: "primary.main" }}
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

          {supportsAlternative ? (
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <FormControl fullWidth size="small">
                <InputLabel>
                  {t("models:label.alternativeHypothesis")}
                </InputLabel>
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
                  <MenuItem value="less">
                    {t("models:alternative.less")}
                  </MenuItem>
                </Select>
              </FormControl>
              {selectedRuns.length === 2 && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: 0.5, display: "block" }}
                >
                  {t("models:label.model1")}:{" "}
                  <strong>{selectedRuns[0].name}</strong>
                  <br />
                  {t("models:label.model2")}:{" "}
                  <strong>{selectedRuns[1].name}</strong>
                </Typography>
              )}
            </Box>
          ) : (
            <Box sx={{ flex: 1 }} />
          )}
        </Box>

        {/* Results */}
        {results && (
          <Box
            sx={{
              mt: 3,
              pt: 2,
              borderTop: "1px solid",
              borderColor: "divider",
            }}
          >
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

            {results.posthoc && results.posthoc.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  {t(
                    POSTHOC_TEST_LABELS[results.test_name] ||
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
      </DialogContent>

      <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
        <Button variant="outlined" onClick={onClose} disabled={loading}>
          {t("common:cancel")}
        </Button>
        <Button
          variant="contained"
          onClick={handleExecuteTest}
          disabled={loading || !countValid || !selectedMetric}
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
      </DialogActions>
    </Dialog>
  );
}

StatisticalTestsModal.propTypes = {
  test: PropTypes.shape({
    name: PropTypes.string,
    display_name: PropTypes.string,
    description: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
    metadata: PropTypes.object,
  }),
  runs: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      status: PropTypes.number.isRequired,
    }),
  ),
  session: PropTypes.object,
  open: PropTypes.bool,
  onClose: PropTypes.func.isRequired,
};
