import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tabs,
  Tab,
  Paper,
  Button,
  CircularProgress,
} from "@mui/material";
import { ExpandMore, ArrowBackIosNew } from "@mui/icons-material";
import { getPipelineById } from "../../../api/pipeline";
import PipelineResultsMetrics from "./ResultsMetrics";
import PipelineResultsGraphs from "./ResultsGraphs";
import PipelineResultsPrediction from "./ResultsPrediction";
import ResultsTabParameters from "../../../pages/results/components/ResultsTabParameters";
import ResultsExploration from "./ResultsExploration";
import DatasetSummaryTable from "../../datasets/DatasetSummaryTable";

const POLL_INTERVAL_MS = 3000;

function normalizeNodeResults(raw, valueKey = null) {
  if (!raw) {
    return [];
  }

  if (typeof raw === "string") {
    return valueKey
      ? [{ node_id: "legacy", [valueKey]: raw }]
      : [{ node_id: "legacy", value: raw }];
  }

  if (typeof raw !== "object") {
    return [];
  }

  const entries = Object.entries(raw);
  if (entries.length === 0) {
    return [];
  }

  const looksGrouped = entries.every(
    ([, value]) => value && typeof value === "object" && !Array.isArray(value),
  );

  if (looksGrouped) {
    return entries.map(([nodeId, value]) => ({
      node_id: value.node_id || nodeId,
      ...value,
    }));
  }

  return [{ node_id: "legacy", ...raw }];
}

function buildBranchResults({
  trainEntries,
  taskEntries,
  metricsEntries,
  predictionEntries,
}) {
  const branches = new Map();

  const ensureBranch = (branchKey) => {
    if (!branches.has(branchKey)) {
      branches.set(branchKey, {
        branchKey,
        modelName: "-",
        taskName: "-",
        datasetName: "Unknown Dataset",
        parameters: null,
        metrics: null,
        prediction: null,
      });
    }
    return branches.get(branchKey);
  };

  [...trainEntries, ...taskEntries].forEach((entry, idx) => {
    const branchKey = entry.model_node_id || entry.node_id || `train-${idx}`;
    const branch = ensureBranch(branchKey);

    branch.modelName = entry.model || entry.info || branch.modelName;
    branch.taskName = entry.task || branch.task_name || branch.taskName;
    branch.datasetName = entry.dataset_name || branch.datasetName;
    branch.parameters = entry.parameters ?? branch.parameters;
  });

  metricsEntries.forEach((entry, idx) => {
    const branchKey = entry.model_node_id || entry.node_id || `metrics-${idx}`;
    const branch = ensureBranch(branchKey);

    branch.datasetName = entry.dataset_name || branch.datasetName;
    branch.modelName = entry.model_name || branch.modelName;
    branch.taskName = entry.task_name || branch.taskName;
    branch.metrics = entry.results || branch.metrics;
  });

  predictionEntries.forEach((entry, idx) => {
    const branchKey =
      entry.model_node_id || entry.node_id || `prediction-${idx}`;
    const branch = ensureBranch(branchKey);

    branch.datasetName = entry.dataset_name || branch.datasetName;
    branch.modelName = entry.model_name || branch.modelName;
    branch.taskName = entry.task_name || branch.taskName;
    branch.prediction = entry.prediction || branch.prediction;
  });

  return Array.from(branches.values());
}

function PipelineResults({ pipelineId, onClose }) {
  const [results, setResults] = useState(null);
  const [trainTab, setTrainTab] = useState(0);
  const [metricsTab, setMetricsTab] = useState(0);
  const [polling, setPolling] = useState(false);
  const pollingRef = useRef(null);

  const hasAnyResult = useCallback((data) => {
    if (!data) return false;
    const hasExpl =
      data.exploration && data.exploration !== "No exploration data";
    const hasTr = data.train && Object.keys(data.train).length > 0;
    const hasAtomized =
      (data.task_and_model && Object.keys(data.task_and_model).length > 0) ||
      (data.metrics_result && Object.keys(data.metrics_result).length > 0);
    const hasPred = data.prediction && data.prediction !== "No prediction data";
    return hasExpl || hasTr || hasAtomized || hasPred;
  }, []);

  useEffect(() => {
    let cancelled = false;

    const fetchResults = async () => {
      try {
        const response = await getPipelineById(pipelineId);
        if (cancelled) return;
        setResults(response);

        if (!hasAnyResult(response)) {
          setPolling(true);
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = setInterval(async () => {
            try {
              const updated = await getPipelineById(pipelineId);
              if (cancelled) return;
              setResults(updated);
              if (hasAnyResult(updated)) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
                setPolling(false);
              }
            } catch (err) {
              console.error("Error polling pipeline results:", err);
            }
          }, POLL_INTERVAL_MS);
        }
      } catch (error) {
        console.error("Error fetching results:", error);
      }
    };

    if (pipelineId) {
      fetchResults();
    }

    return () => {
      cancelled = true;
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [pipelineId, hasAnyResult]);

  const handleTabChange = (event, newValue) => {
    setTrainTab(newValue);
  };

  const handleMetricsTabChange = (event, newValue) => {
    setMetricsTab(newValue);
  };

  if (!results) {
    return <Typography>Loading results...</Typography>;
  }

  const taskEntries = normalizeNodeResults(results.task_and_model);
  const trainEntries = normalizeNodeResults(results.train);
  const metricsEntries = normalizeNodeResults(results.metrics_result);
  const predictionEntries = normalizeNodeResults(
    results.prediction,
    "prediction",
  );

  const branchResults = buildBranchResults({
    trainEntries,
    taskEntries,
    metricsEntries,
    predictionEntries,
  });

  const hasExploration =
    results.exploration && results.exploration !== "No exploration data";
  const hasTrain =
    branchResults.filter((branch) => branch.parameters).length > 0;
  const hasMetrics =
    branchResults.filter((branch) => !!branch.metrics).length > 0;
  const hasPrediction =
    branchResults.filter((branch) => !!branch.prediction).length > 0;

  const steps = Array.isArray(results.steps) ? results.steps : [];
  const dataSelectorSteps = steps.filter((s) => s.type === "DataSelector");
  const splitDataSteps = steps.filter((s) => s.type === "SplitData");
  const retrieveModelSteps = steps.filter((s) => s.type === "RetrieveModel");
  const totalRows = dataSelectorSteps[0]?.config?.total_rows ?? null;

  const hasDataSelector = dataSelectorSteps.length > 0;
  const hasSplitData = splitDataSteps.length > 0;
  const hasRetrieveModel = retrieveModelSteps.length > 0;

  const splitSize = (ratio) =>
    totalRows != null && ratio != null ? Math.round(ratio * totalRows) : null;

  const formatColumns = (cols) =>
    Array.isArray(cols) && cols.length > 0 ? cols.join(", ") : "-";

  if (
    !hasExploration &&
    !hasTrain &&
    !hasMetrics &&
    !hasPrediction &&
    !hasDataSelector &&
    !hasSplitData &&
    !hasRetrieveModel
  ) {
    return (
      <Box sx={{ p: 4 }}>
        {onClose && (
          <Button startIcon={<ArrowBackIosNew />} onClick={onClose}>
            Volver
          </Button>
        )}
        {polling ? (
          <Box display="flex" alignItems="center" gap={2} mt={2}>
            <CircularProgress size={24} />
            <Typography>
              Pipeline is running. Results will appear automatically…
            </Typography>
          </Box>
        ) : (
          <Typography>No results available</Typography>
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {polling && (
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <CircularProgress size={20} />
          <Typography variant="body2">
            Pipeline is running. Remaining results will appear automatically…
          </Typography>
        </Box>
      )}

      {hasDataSelector && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Data Selector</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2} display="flex" flexDirection="column" gap={3}>
              {dataSelectorSteps.map((step) => {
                const cfg = step.config || {};
                return (
                  <Paper sx={{ width: "100%", p: 3 }} key={step.id}>
                    <Typography variant="subtitle1">
                      Dataset: {cfg.name || "-"}
                    </Typography>
                    <Typography variant="body2" sx={{ color: "gray", mb: 2 }}>
                      {cfg.total_rows ?? "?"} rows × {cfg.total_columns ?? "?"}{" "}
                      columns
                      {cfg.task ? ` | ${cfg.task}` : ""}
                    </Typography>
                    {cfg.id != null && (
                      <DatasetSummaryTable
                        datasetId={Number(cfg.id)}
                        isEditable={false}
                      />
                    )}
                  </Paper>
                );
              })}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasSplitData && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Split Data</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2} display="flex" flexDirection="column" gap={3}>
              {splitDataSteps.map((step) => {
                const cfg = step.config || {};
                const splits = cfg.splits || {};
                return (
                  <Paper sx={{ width: "100%", p: 3 }} key={step.id}>
                    <Typography variant="body2" sx={{ mb: 0.5 }}>
                      <strong>Input columns:</strong>{" "}
                      {formatColumns(cfg.input_columns)}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 2 }}>
                      <strong>Output columns:</strong>{" "}
                      {formatColumns(cfg.output_columns)}
                    </Typography>
                    {["train", "validation", "test"].map((key) => {
                      const ratio = splits[key];
                      const size = splitSize(ratio);
                      return (
                        <Typography
                          key={key}
                          variant="body2"
                          sx={{ color: "gray" }}
                        >
                          {key.charAt(0).toUpperCase() + key.slice(1)}:{" "}
                          {ratio != null ? `${Math.round(ratio * 100)}%` : "-"}
                          {size != null ? ` (~${size} rows)` : ""}
                        </Typography>
                      );
                    })}
                  </Paper>
                );
              })}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasRetrieveModel && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Retrieve Model</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2} display="flex" flexDirection="column" gap={3}>
              {retrieveModelSteps.map((step) => {
                const cfg = step.config || {};
                return (
                  <Paper sx={{ width: "100%", p: 3 }} key={step.id}>
                    <Typography variant="subtitle1">
                      {cfg.model || "-"}
                    </Typography>
                    <Typography variant="body2" sx={{ color: "gray", mb: 1 }}>
                      {cfg.task ? `Task: ${cfg.task}` : ""}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 0.5 }}>
                      <strong>Input columns:</strong>{" "}
                      {formatColumns(cfg.input_columns)}
                    </Typography>
                    {cfg.model_path && (
                      <Typography
                        variant="caption"
                        sx={{ color: "gray", wordBreak: "break-all" }}
                      >
                        {cfg.model_path}
                      </Typography>
                    )}
                  </Paper>
                );
              })}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasExploration && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Exploration</Typography>
          </AccordionSummary>
          <AccordionDetails
            sx={{
              borderTop: "1px solid #383838",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <Box mx={10} my={2}>
              <ResultsExploration pipelineId={pipelineId} />
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasTrain && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Train</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2} display="flex" flexDirection="column" gap={3}>
              {branchResults
                .filter((branch) => branch.parameters)
                .map((branch, branchIndex) => {
                  const paramData = { parameters: branch.parameters };

                  return (
                    <Paper sx={{ width: "100%" }} key={branch.branchKey}>
                      <Box sx={{ px: 3, pt: 2, pb: 1 }}>
                        <Typography variant="subtitle1">
                          Path {branchIndex + 1} | Dataset: {branch.datasetName}
                        </Typography>
                        <Typography variant="body2" sx={{ color: "gray" }}>
                          {branch.taskName} | {branch.modelName}
                        </Typography>
                      </Box>

                      <Tabs
                        value={trainTab}
                        onChange={handleTabChange}
                        variant="scrollable"
                      >
                        <Tab label="Info" />
                        <Tab label="Parameters" />
                      </Tabs>

                      <Box sx={{ p: 3 }}>
                        {trainTab === 0 && (
                          <Box>
                            <Typography variant="subtitle1">
                              Model Name
                            </Typography>
                            <Typography variant="p" sx={{ color: "gray" }}>
                              {branch.modelName}
                            </Typography>
                          </Box>
                        )}
                        {trainTab === 1 && (
                          <Box>
                            <ResultsTabParameters runData={paramData} />
                          </Box>
                        )}
                      </Box>
                    </Paper>
                  );
                })}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasMetrics && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Metrics</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2} display="flex" flexDirection="column" gap={3}>
              {branchResults
                .filter((branch) => !!branch.metrics)
                .map((branch, branchIndex) => (
                  <Paper sx={{ width: "100%" }} key={branch.branchKey}>
                    <Box sx={{ px: 3, pt: 2, pb: 1 }}>
                      <Typography variant="subtitle1">
                        Path {branchIndex + 1} | Dataset: {branch.datasetName}
                      </Typography>
                      <Typography variant="body2" sx={{ color: "gray" }}>
                        {branch.taskName} | {branch.modelName}
                      </Typography>
                    </Box>

                    <Tabs
                      value={metricsTab}
                      onChange={handleMetricsTabChange}
                      variant="scrollable"
                    >
                      <Tab label="Metrics" />
                      <Tab label="Graphs" />
                    </Tabs>

                    <Box sx={{ p: 3 }}>
                      {metricsTab === 0 && (
                        <Box>
                          <PipelineResultsMetrics
                            metricsData={branch.metrics}
                          />
                        </Box>
                      )}
                      {metricsTab === 1 && (
                        <Box>
                          <PipelineResultsGraphs metrics={branch.metrics} />
                        </Box>
                      )}
                    </Box>
                  </Paper>
                ))}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasPrediction && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Prediction</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2} display="flex" flexDirection="column" gap={3}>
              {branchResults
                .filter((branch) => !!branch.prediction)
                .map((branch, branchIndex) => (
                  <Box key={branch.branchKey}>
                    <Typography variant="subtitle1">
                      Path {branchIndex + 1} | Dataset: {branch.datasetName}
                    </Typography>
                    <Typography variant="body2" sx={{ color: "gray", mb: 1 }}>
                      {branch.taskName} | {branch.modelName}
                    </Typography>
                    <PipelineResultsPrediction prediction={branch.prediction} />
                  </Box>
                ))}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
}

export default PipelineResults;
