import { actionsColumns } from "./actionsColumns";
import { initialColumns } from "./initialColumns";
import QueryStatsIcon from "@mui/icons-material/QueryStats";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import InfoIcon from "@mui/icons-material/Info";
import { PlayArrow } from "@mui/icons-material";
import { styled } from "@mui/system";
import DeleteIcon from "@mui/icons-material/Delete";

export const extractColumns = (
  rawMetrics,
  rawRuns,
  datasetId,
  handleRun,
  handleRunResultsOpen,
  handlePrediction,
  handleExplainer,
  handleDeleteRun,
) => {
  console.log("Extracting columns with metrics:", rawMetrics);
  // ===== METRICS (only test metrics) =====
  const metrics = rawMetrics.map((metric) => ({
    accessorKey: metric.name,
    header: metric.name,
    Cell: ({ row, cell }) => {
      if ([0, 1, 2].includes(row.original.status))
        // Not Started, Delivered, Started
        return "-";

      return row.original.test_metrics?.[metric.name] !== undefined
        ? Number(row.original.test_metrics[metric.name]).toFixed(2)
        : "-";
    },
  }));

  // ===== ACTIONS =====
  const actions = actionsColumns([
    {
      title: "Run",
      Icon: PlayArrow,
      handleAction: handleRun,
      requiresFinished: false,
      alwaysEnabled: false,
    },
    {
      title: "Details",
      Icon: InfoIcon,
      handleAction: handleRunResultsOpen,
      requiresFinished: false,
      alwaysEnabled: true,
    },
    {
      title: "Predict",
      Icon: TrendingUpIcon,
      handleAction: (run) => handlePrediction(run, datasetId),
      requiresFinished: true,
      alwaysEnabled: false,
    },
    {
      title: "Explain",
      Icon: QueryStatsIcon,
      handleAction: handleExplainer,
      requiresFinished: true,
      alwaysEnabled: false,
    },
    {
      title: "Delete",
      Icon: styled(DeleteIcon)(({ theme }) => ({
        color: theme.palette.error.main,
      })),
      handleAction: handleDeleteRun,
      requiresFinished: false,
      alwaysEnabled: false,
    },
  ]);

  // ===== MRT NESTED COLUMN GROUPS =====
  const columns = [
    {
      id: "info-group",
      header: "Info",
      columns: [...initialColumns],
    },
    {
      id: "test-metrics-group",
      header: "Test Metrics",
      columns: [...metrics],
    },
    {
      id: "actions-group",
      header: "Actions",
      columns: [...actions],
    },
  ];

  // ===== VISIBILITY (hide nothing by default — all visible) =====
  const columnVisibilityModel = {};

  return { columns, columnVisibilityModel };
};
