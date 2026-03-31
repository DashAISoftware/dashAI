import PropTypes from "prop-types";
import React, { useEffect, useMemo, useState } from "react";
import { Alert, AlertTitle } from "@mui/material";
import { useSnackbar } from "notistack";
import graphsMaking from "../../../pages/results/constants/graphsMaking";
import layoutMaking from "../../../pages/results/constants/layoutMaking";

import ResultsGraphsLayout from "../../../pages/results/components/ResultsGraphsLayout";

function PipelineResultsGraphs({ metrics }) {
  const { enqueueSnackbar } = useSnackbar();
  const [selectedChart, setSelectedChart] = useState("radar");
  const [selectedParameters, setSelectedParameters] = useState([]);
  const [showCustomMetrics, setShowCustomMetrics] = useState(false);
  const [selectedGeneralMetric, setSelectedGeneralMetric] = useState("test");

  const handleChangeChart = (chartType) => {
    setSelectedChart(chartType);
  };

  const handleToggleParameter = (parameter) => {
    const updatedParameters = selectedParameters.includes(parameter)
      ? selectedParameters.filter((param) => param !== parameter)
      : [...selectedParameters, parameter];
    setSelectedParameters(updatedParameters);
  };

  const handleToggleMetrics = () => {
    setShowCustomMetrics(!showCustomMetrics);
    setSelectedParameters([]);
  };

  const {
    concatenatedMetrics,
    tabularMetrics,
    chartData,
    filteredDataProcess,
    chartError,
  } = useMemo(() => {
    if (!metrics || Object.keys(metrics).length === 0) {
      return {
        concatenatedMetrics: [],
        tabularMetrics: [],
        chartData: {},
        filteredDataProcess: [],
        chartError: null,
      };
    }

    try {
      const phases = Object.keys(metrics);
      if (phases.length === 0) {
        return {
          concatenatedMetrics: [],
          tabularMetrics: [],
          chartData: {},
          filteredDataProcess: [],
          chartError: null,
        };
      }
      const metricNames = Object.keys(metrics[phases[0]] ?? {});
      const tabularMetrics = [];

      phases.forEach((phase) => {
        metricNames.forEach((metric) => {
          tabularMetrics.push(`${phase} ${metric}`);
        });
      });

      const concatenatedMetrics = Array.from(
        new Set(phases.concat(metricNames)),
      );

      let parameterIndex = [];
      let generalParameters = [];

      if (showCustomMetrics) {
        parameterIndex = selectedParameters.map((param) =>
          tabularMetrics.indexOf(param),
        );
      } else {
        const criteria = {};
        concatenatedMetrics.forEach((item) => {
          criteria[item] = item;
        });

        tabularMetrics.forEach((metric, index) => {
          Object.entries(criteria).forEach(([metricName, substring]) => {
            if (
              selectedGeneralMetric === metricName &&
              metric.includes(substring)
            ) {
              parameterIndex.push(index);
              generalParameters.push(metric);
            }
          });
        });
      }

      const syntheticRun = {
        status: 3,
        train_metrics: metrics.train,
        validation_metrics: metrics.validation,
        test_metrics: metrics.test,
      };

      const graphsToView = {};
      const numericValues = [];
      ["train", "validation", "test"].forEach((split) => {
        metricNames.forEach((metric) => {
          numericValues.push(metrics[split][metric]);
        });
      });

      const relevantNumericValues = parameterIndex.map(
        (index) => numericValues[index],
      );

      graphsMaking(
        graphsToView,
        syntheticRun,
        relevantNumericValues,
        showCustomMetrics,
        selectedParameters,
        generalParameters,
        0,
      );

      const { generalLayout, pieLayout } = layoutMaking(
        selectedChart,
        graphsToView,
      );

      const graphsToViewKeys = Object.keys(graphsToView);
      const radarValues = graphsToView[graphsToViewKeys[0]];
      const barValues = graphsToView[graphsToViewKeys[1]];
      const pieValues = graphsToView[graphsToViewKeys[2]];

      return {
        concatenatedMetrics,
        tabularMetrics,
        chartData: {
          generalLayout,
          pieLayout,
          radarValues,
          barValues,
          pieValues,
        },
        filteredDataProcess: [syntheticRun],
        chartError: null,
      };
    } catch (err) {
      return {
        concatenatedMetrics: [],
        tabularMetrics: [],
        chartData: {},
        filteredDataProcess: [],
        chartError: err,
      };
    }
  }, [
    metrics,
    selectedParameters,
    selectedChart,
    showCustomMetrics,
    selectedGeneralMetric,
  ]);

  useEffect(() => {
    if (!chartError) return;
    enqueueSnackbar("Error processing metrics", { variant: "error" });
    console.error(chartError);
  }, [chartError, enqueueSnackbar]);

  return (
    <>
      {filteredDataProcess.length === 0 ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <AlertTitle>No metric data available</AlertTitle>
          Please provide valid metrics to render the graphs.
        </Alert>
      ) : (
        <ResultsGraphsLayout
          selectedChart={selectedChart}
          handleChangeChart={handleChangeChart}
          showCustomMetrics={showCustomMetrics}
          handleToggleMetrics={handleToggleMetrics}
          tabularMetrics={tabularMetrics}
          selectedParameters={selectedParameters}
          handleToggleParameter={handleToggleParameter}
          selectedGeneralMetric={selectedGeneralMetric}
          setSelectedGeneralMetric={setSelectedGeneralMetric}
          setSelectedParameters={setSelectedParameters}
          concatenatedMetrics={concatenatedMetrics}
          chartData={chartData}
        />
      )}
    </>
  );
}

export default PipelineResultsGraphs;
