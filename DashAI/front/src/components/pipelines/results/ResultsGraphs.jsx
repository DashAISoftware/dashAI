import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";
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
  const [concatenatedMetrics, setConcatenatedMetrics] = useState([]);
  const [tabularMetrics, setTabularMetrics] = useState([]);
  const [chartData, setChartData] = useState({});
  const [filteredDataProcess, setFilteredDataProcess] = useState([]);

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

  useEffect(() => {
    const processData = () => {
      try {
        const phases = Object.keys(metrics);
        const metricNames = Object.keys(metrics[phases[0]]);
        const tabularMetrics = [];

        phases.forEach((phase) => {
          metricNames.forEach((metric) => {
            tabularMetrics.push(`${phase} ${metric}`);
          });
        });

        const concatenatedMetrics = Array.from(
          new Set(phases.concat(metricNames)),
        );
        setConcatenatedMetrics(concatenatedMetrics);
        setTabularMetrics(tabularMetrics);

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

        const newFilteredData = [syntheticRun];
        setFilteredDataProcess(newFilteredData);

        const graphsToView = {};
        let pieCounter = 0;

        const numericValues = [];
        ["train", "validation", "test"].forEach((split) => {
          metricNames.forEach((metric) => {
            const metricData = metrics[split][metric];
            // Handle both old format (direct number) and new format (object with value and std_value)
            const value = metricData?.value ?? metricData;
            numericValues.push(value);
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
          pieCounter,
        );

        const { generalLayout, pieLayout } = layoutMaking(
          selectedChart,
          graphsToView,
        );

        const graphsToViewKeys = Object.keys(graphsToView);
        const radarValues = graphsToView[graphsToViewKeys[0]];
        const barValues = graphsToView[graphsToViewKeys[1]];
        const pieValues = graphsToView[graphsToViewKeys[2]];

        setChartData({
          generalLayout,
          pieLayout,
          radarValues,
          barValues,
          pieValues,
        });
      } catch (err) {
        enqueueSnackbar("Error processing metrics", { variant: "error" });
        console.error(err);
      }
    };

    processData();
  }, [metrics, selectedParameters, selectedChart]);

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
