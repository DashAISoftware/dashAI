export const isFiniteMetricValue = (value) =>
  typeof value === "number" && Number.isFinite(value);

export const getNumericMetrics = (metrics = {}) =>
  Object.fromEntries(
    Object.entries(metrics).filter(([, value]) => isFiniteMetricValue(value)),
  );

export const getNumericMetricEntries = (metrics = {}) =>
  Object.entries(getNumericMetrics(metrics));

export const formatScalarMetricsForChart = (metrics = {}) => {
  const now = new Date().toISOString();

  return Object.fromEntries(
    getNumericMetricEntries(metrics).map(([metricName, value]) => [
      metricName,
      [{ step: 1, value, timestamp: now }],
    ]),
  );
};
