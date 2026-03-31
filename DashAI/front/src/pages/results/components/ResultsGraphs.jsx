import PropTypes from "prop-types";
import React, { useEffect, useMemo, useState } from "react";
import { Alert, AlertTitle } from "@mui/material";
import { useSnackbar } from "notistack";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

import graphsMaking from "../constants/graphsMaking";
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

  const [selectedChart, setSelectedChart] = useState("bar");
  const [excludedMetricsBySplit, setExcludedMetricsBySplit] = useState({});

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

  const defaultSplit = useMemo(() => {
    if (availableMetrics.test.length > 0) return "test";
    if (availableMetrics.validation.length > 0) return "validation";
    if (availableMetrics.train.length > 0) return "train";
    return "test";
  }, [availableMetrics]);

  // Controlled or uncontrolled split
  const selectedSplit = splitProp ?? defaultSplit;

  const selectedMetrics = useMemo(() => {
    const available = availableMetrics[selectedSplit] ?? [];
    const excluded = excludedMetricsBySplit[selectedSplit] ?? [];
    if (excluded.length === 0) return available;
    const excludedSet = new Set(excluded);
    return available.filter((metric) => !excludedSet.has(metric));
  }, [availableMetrics, excludedMetricsBySplit, selectedSplit]);

  const { chartData, chartError } = useMemo(() => {
    if (finishedRuns.length === 0 || selectedMetrics.length === 0) {
      return { chartData: {}, chartError: null };
    }

    try {
      const metricsKey = `${selectedSplit}_metrics`;
      const graphsToView = {};

      finishedRuns.forEach((run, idx) => {
        const metricsObj = run[metricsKey] ?? {};
        const values = selectedMetrics.map((m) => {
          const v = metricsObj[m];
          if (v === undefined || v === null) return null;
          if (Array.isArray(v)) return v[v.length - 1]?.value ?? null;
          return typeof v === "number" ? v : null;
        });
        graphsMaking(graphsToView, run, selectedMetrics, values, idx, theme);
      });

      const { generalLayout } = layoutMaking(
        selectedChart,
        graphsToView,
        theme,
      );
      return { chartData: { generalLayout, ...graphsToView }, chartError: null };
    } catch (error) {
      return { chartData: {}, chartError: error };
    }
  }, [
    finishedRuns,
    selectedSplit,
    selectedMetrics,
    selectedChart,
    theme,
  ]);

  useEffect(() => {
    if (!chartError) return;
    enqueueSnackbar(t("models:error.errorProcesingExperimentResults"), {
      variant: "error",
    });
    console.error(chartError);
  }, [chartError, enqueueSnackbar, t]);

  const handleChangeChart = (chartType) => setSelectedChart(chartType);
  const handleToggleMetric = (metric) => {
    setExcludedMetricsBySplit((prev) => {
      const currentExcluded = new Set(prev[selectedSplit] ?? []);
      if (currentExcluded.has(metric)) {
        currentExcluded.delete(metric);
      } else {
        currentExcluded.add(metric);
      }
      return { ...prev, [selectedSplit]: Array.from(currentExcluded) };
    });
  };
  const handleSelectAll = () =>
    setExcludedMetricsBySplit((prev) => ({ ...prev, [selectedSplit]: [] }));
  const handleClearAll = () =>
    setExcludedMetricsBySplit((prev) => ({
      ...prev,
      [selectedSplit]: availableMetrics[selectedSplit] ?? [],
    }));

  if (finishedRuns.length === 0) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        <AlertTitle>No information from the experiments</AlertTitle>
        There are no completed experiments or all have an error status.
      </Alert>
    );
  }

  const currentMetrics = availableMetrics[selectedSplit] ?? [];

  return (
    <ResultsGraphsLayout
      selectedChart={selectedChart}
      handleChangeChart={handleChangeChart}
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
