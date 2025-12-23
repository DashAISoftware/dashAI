import { actionsColumns } from "./actionsColumns";
import { initialColumns } from "./initialColumns";
import QueryStatsIcon from "@mui/icons-material/QueryStats";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import InfoIcon from "@mui/icons-material/Info";
import { PlayArrow } from "@mui/icons-material";
import { Icon } from "@mui/material";
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
  // ===== METRICS (only test metrics) =====
  const metrics = rawMetrics.map((metric) => ({
    field: `test_${metric.name}`,
    headerName: `test_${metric.name}`,
    renderCell: ({ row, value }) => {
      if (["Started", "Delivered"].includes(row.status)) return "-";

      const v = Array.isArray(value) ? value[0] : null;
      return typeof v === "number" ? v.toFixed(2) : "-";
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
      handleAction: (runId) => handlePrediction(runId, datasetId),
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

  // ===== GROUPING =====
  const columnGroupingModel = [
    { groupId: "Info", children: [...initialColumns] },
    { groupId: "Test Metrics", children: [...metrics] },
    { groupId: "Actions", children: [...actions] },
  ];

  // ===== VISIBILITY (hide everything except test metrics) =====
  let columnVisibilityModel = {
    created: false,
    last_modified: false,
    start_time: false,
    end_time: false,
  };

  // hide nothing from test metrics (show them all)
  metrics.forEach((m) => {
    columnVisibilityModel[m.field] = true;
  });

  const columns = [...initialColumns, ...metrics, ...actions];

  return { columns, columnGroupingModel, columnVisibilityModel };
};
