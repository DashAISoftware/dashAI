import PropTypes from "prop-types";
import React, { useEffect, useMemo, useState } from "react";
import { Alert, AlertTitle } from "@mui/material";
import { useSnackbar } from "notistack";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

import { getComponents } from "../../../api/component";
import { heatmapMaking, smallMultiplesMaking } from "../constants/graphsMaking";
import layoutMaking from "../constants/layoutMaking";
import ResultsGraphsLayout from "./ResultsGraphsLayout";

function ResultsGraphs({
  runs,
  selectedSplit: splitProp = undefined,
  onSplitChange = undefined,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const { t } = useTranslation(["models"]);

  // Internal split state — used only when no controlled prop is provided
  const [internalSplit, setInternalSplit] = useState("test");
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [chartData, setChartData] = useState({});
  // { MetricName: { maximize: bool } } — fetched once on mount
  const [metricsMetadata, setMetricsMetadata] = useState({});

  // Controlled or uncontrolled split
  const selectedSplit = splitProp ?? internalSplit;
  const handleChangeSplit = onSplitChange ?? setInternalSplit;

  // Fetch metric maximize direction once on mount
  useEffect(() => {
    getComponents({ selectTypes: ["Metric"] })
      .then((components) => {
        const meta = {};
        components.forEach((c) => {
          meta[c.name] = c.metadata;
        });
        setMetricsMetadata(meta);
      })
      .catch((error) => {
        console.error(
          "Failed to fetch metric metadata for results heatmap.",
          error,
        );
        enqueueSnackbar(t("models:error.metricMetadataFetch"), {
          variant: "warning",
        });
      });
  }, [enqueueSnackbar, t]);

  const finishedRuns = useMemo(
    () => runs.filter((r) => r.status === 3),
    [runs],
  );

  const availableMetrics = useMemo(() => {
    const sets = { train: new Set(), validation: new Set(), test: new Set() };
    finishedRuns.forEach((run) => {
      if (run.train_metrics)
        Object.keys(run.train_metrics).forEach((m) => sets.train.add(m));
      if (run.validation_metrics)
        Object.keys(run.validation_metrics).forEach((m) =>
          sets.validation.add(m),
        );
      if (run.test_metrics)
        Object.keys(run.test_metrics).forEach((m) => sets.test.add(m));
    });
    return {
      train: Array.from(sets.train),
      validation: Array.from(sets.validation),
      test: Array.from(sets.test),
    };
  }, [finishedRuns]);

  // Auto-select a split only when running in uncontrolled mode
  useEffect(() => {
    if (splitProp !== undefined) return;
    if (availableMetrics.test.length > 0) setInternalSplit("test");
    else if (availableMetrics.validation.length > 0)
      setInternalSplit("validation");
    else if (availableMetrics.train.length > 0) setInternalSplit("train");
  }, [availableMetrics, splitProp]);

  useEffect(() => {
    setSelectedMetrics(availableMetrics[selectedSplit] ?? []);
  }, [selectedSplit, availableMetrics]);

  useEffect(() => {
    if (finishedRuns.length === 0 || selectedMetrics.length === 0) {
      setChartData({});
      return;
    }

    try {
      const metricsKey = `${selectedSplit}_metrics`;

      // Bar view: one small chart per metric (small multiples) instead of
      // one combined chart, so metrics with different scales/ranges never
      // share an axis. Every run keeps the same color across all panels.
      const { panels, legend, yaxis } = smallMultiplesMaking(
        finishedRuns,
        selectedMetrics,
        metricsKey,
        theme,
        metricsMetadata,
      );

      // Heatmap is a single all-runs trace, unchanged.
      const heatmap = heatmapMaking(
        finishedRuns,
        selectedMetrics,
        metricsKey,
        theme,
        metricsMetadata,
      );

      const { generalLayout } = layoutMaking("heatmap", {}, theme);
      setChartData({ generalLayout, bar: panels, legend, yaxis, heatmap });
    } catch (error) {
      enqueueSnackbar(t("models:error.errorProcesingExperimentResults"), {
        variant: "error",
      });
      console.error(error);
    }
  }, [
    finishedRuns,
    selectedSplit,
    selectedMetrics,
    theme,
    metricsMetadata,
    enqueueSnackbar,
    t,
  ]);

  const handleToggleMetric = (metric) => {
    const canonicalOrder = availableMetrics[selectedSplit] ?? [];
    setSelectedMetrics((prev) => {
      if (prev.includes(metric)) {
        return prev.filter((m) => m !== metric);
      }
      const next = new Set([...prev, metric]);
      return canonicalOrder.filter((m) => next.has(m));
    });
  };
  const handleSelectAll = () =>
    setSelectedMetrics(availableMetrics[selectedSplit] ?? []);
  const handleClearAll = () => setSelectedMetrics([]);

  if (finishedRuns.length === 0) {
    return (
      <Alert severity="warning" sx={{ mb: 4 }}>
        <AlertTitle>No information from the experiments</AlertTitle>
        There are no completed experiments or all have an error status.
      </Alert>
    );
  }

  const currentMetrics = availableMetrics[selectedSplit] ?? [];

  return (
    <ResultsGraphsLayout
      currentMetrics={currentMetrics}
      selectedMetrics={selectedMetrics}
      handleToggleMetric={handleToggleMetric}
      handleSelectAll={handleSelectAll}
      handleClearAll={handleClearAll}
      chartData={chartData}
    />
  );
}

ResultsGraphs.propTypes = {
  runs: PropTypes.array.isRequired,
  selectedSplit: PropTypes.string,
  onSplitChange: PropTypes.func,
};

export default ResultsGraphs;
