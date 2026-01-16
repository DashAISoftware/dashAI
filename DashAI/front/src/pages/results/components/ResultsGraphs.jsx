import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";
import { Alert, AlertTitle } from "@mui/material";
import { useSnackbar } from "notistack";

import graphsMaking from "../constants/graphsMaking";
import layoutMaking from "../constants/layoutMaking";
import ResultsGraphsLayout from "./ResultsGraphsLayout";
import { useTranslation } from "react-i18next";

function ResultsGraphs({ runs }) {
  const { enqueueSnackbar } = useSnackbar();
  const [selectedChart, setSelectedChart] = useState("radar");
  const [selectedParameters, setSelectedParameters] = useState([]);
  const [showCustomMetrics, setShowCustomMetrics] = useState(false);
  const [selectedGeneralMetric, setSelectedGeneralMetric] = useState("test");

  const [concatenatedMetrics, setConcatenatedMetrics] = useState([]);
  const [tabularMetrics, setTabularMetrics] = useState([]);
  const [chartData, setChartData] = useState({});
  const [filteredDataProcess, setFilteredDataProcess] = useState([]);
  const { t } = useTranslation(["models"]);

  const handleChangeChart = (chartType) => {
    setSelectedChart(chartType);
  };

  const handleToggleParameter = (parameter) => {
    setSelectedParameters((prev) =>
      prev.includes(parameter)
        ? prev.filter((p) => p !== parameter)
        : [...prev, parameter],
    );
  };

  const handleToggleMetrics = () => {
    setShowCustomMetrics((prev) => !prev);
    setSelectedParameters([]);
  };

  useEffect(() => {
    if (!runs) return;

    const processData = async () => {
      try {
        // Only take finished runs
        const finished = runs.filter((item) => item.status === 3); // Finished
        setFilteredDataProcess(finished);

        if (finished.length === 0) return;

        const graphsToView = {};
        let parameterIndex = [];
        const generalParameters = [];
        let pieCounter = 0;

        // Extract metrics
        const extractedMetrics = finished.map((item) => {
          const metrics = {};
          Object.keys(item).forEach((key) => {
            if (key.includes("metrics")) {
              metrics[key] = item[key];
            }
          });
          return metrics;
        });

        if (extractedMetrics.length > 0) {
          const metricsOrder = Object.keys(extractedMetrics[0]);
          const metricsValuesOrder = Object.keys(
            extractedMetrics[0][metricsOrder[0]],
          );

          const concatenated = metricsOrder
            .map((m) => m.split("_")[0])
            .concat(metricsValuesOrder);

          setConcatenatedMetrics(concatenated);

          // Build table metrics
          const tableMetrics = [];
          metricsOrder.forEach((metricType) => {
            metricsValuesOrder.forEach((metric) => {
              tableMetrics.push(`${metricType.split("_")[0]} ${metric}`);
            });
          });
          setTabularMetrics(tableMetrics);

          // Pick indices of selected parameters
          if (showCustomMetrics) {
            parameterIndex = selectedParameters.map((p) =>
              tableMetrics.indexOf(p),
            );
          } else if (selectedGeneralMetric.length > 0) {
            const criteria = {};
            concatenated.forEach((item) => (criteria[item] = item));

            tableMetrics.forEach((metric, index) => {
              Object.entries(criteria).forEach(([metName, substring]) => {
                if (
                  selectedGeneralMetric === metName &&
                  metric.includes(substring)
                ) {
                  parameterIndex.push(index);
                  generalParameters.push(metric);
                }
              });
            });
          }

          // Build values for each run
          finished.forEach((item) => {
            const numericValues = [];

            metricsOrder.forEach((metricType) => {
              const values = item[metricType];
              metricsValuesOrder.forEach((metric) => {
                numericValues.push(values[metric]);
              });
            });

            const relevantValues = parameterIndex.map(
              (index) => numericValues[index],
            );

            graphsMaking(
              graphsToView,
              item,
              relevantValues,
              showCustomMetrics,
              selectedParameters,
              generalParameters,
              pieCounter,
            );

            pieCounter += 1;
          });

          // Generate layouts
          const { generalLayout, pieLayout } = layoutMaking(
            selectedChart,
            graphsToView,
          );

          const keys = Object.keys(graphsToView);
          const radarValues = graphsToView[keys[0]];
          const barValues = graphsToView[keys[1]];
          const pieValues = graphsToView[keys[2]];

          setChartData({
            generalLayout,
            pieLayout,
            radarValues,
            barValues,
            pieValues,
          });
        }
      } catch (error) {
        enqueueSnackbar(t("models:error.errorProcesingExperimentResults"), {
          variant: "error",
        });
        console.error(error);
      }
    };

    processData();
  }, [runs, selectedParameters, selectedChart, showCustomMetrics]);

  return (
    <>
      {filteredDataProcess.length === 0 ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <AlertTitle>No information from the experiments</AlertTitle>
          There are no completed experiments or all have an error status.
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

ResultsGraphs.propTypes = {
  runs: PropTypes.array.isRequired,
};

export default ResultsGraphs;
