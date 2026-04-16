export const getTabsResultsDetails = (t) => [
  { label: t("common:info"), value: 0, disabled: false },
  // { label: "Parameters", value: 1, disabled: false },
  // { label: "Metrics", value: 2, disabled: false },
  {
    label: t("models:label.hyperparameterOptimizationPlots"),
    value: 3,
    disabled: false,
  },
  // { label: "Artifacts", value: 3, disabled: true },
  // { label: "Predict", value: 4, disabled: false },
];
