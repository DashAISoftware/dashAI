import { actionsColumns } from "./actionsColumns";
import { initialColumns } from "./initialColumns";
import QueryStatsIcon from "@mui/icons-material/QueryStats";
import PsychologyAltIcon from "@mui/icons-material/PsychologyAlt";
import InfoIcon from "@mui/icons-material/Info";

export const extractColumns = (
  rawMetrics,
  rawRuns,
  datasetId,
  handleRunResultsOpen,
  handlePrediction,
  handleExplainer,
) => {
  // extract metrics
  let metrics = [];
  for (const metric of rawMetrics) {
    metrics = [
      ...metrics,
      { field: `train_${metric.name}` },
      { field: `test_${metric.name}` },
      { field: `val_${metric.name}` },
    ];
  }

  // extract parameters
  let distinctParameters = {};
  for (const run of rawRuns) {
    distinctParameters = { ...distinctParameters, ...run.parameters };
  }
  const parameters = Object.keys(distinctParameters).map((name) => {
    return { field: name };
  });

  const actions = actionsColumns([
    {
      title: "Details",
      Icon: InfoIcon,
      handleAction: handleRunResultsOpen,
    },
    {
      title: "Predict",
      Icon: QueryStatsIcon,
      handleAction: (runId) => handlePrediction(runId, datasetId),
    },
    {
      title: "Explain",
      Icon: PsychologyAltIcon,
      handleAction: handleExplainer,
    },
  ]);

  // column grouping
  const columnGroupingModel = [
    { groupId: "Info", children: [...initialColumns] },
    { groupId: "Metrics", children: [...metrics] },
    { groupId: "Parameters", children: [...parameters] },
    { groupId: "Actions", children: [...actions] },
  ];

  // column visibility
  let columnVisibilityModel = {
    created: false,
    last_modified: false,
    start_time: false,
    end_time: false,
  };
  [...metrics, ...parameters].forEach((col) => {
    if (col.field.includes("test")) {
      return; // skip this iteration and proceed with the next one
    }
    columnVisibilityModel = { ...columnVisibilityModel, [col.field]: false };
  });

  const columns = [...initialColumns, ...metrics, ...parameters, ...actions];

  return { columns, columnGroupingModel, columnVisibilityModel };
};
