import React from "react";
import TableChartIcon from "@mui/icons-material/TableChart";
import BarChartIcon from "@mui/icons-material/BarChart";
import ScatterPlotIcon from "@mui/icons-material/ScatterPlot";
import TimelineIcon from "@mui/icons-material/Timeline";
import FunctionsIcon from "@mui/icons-material/Functions";

// Category to icon mapping
const CATEGORY_ICONS = {
  Statistical: FunctionsIcon,
  Distribution: BarChartIcon,
  Relationship: ScatterPlotIcon,
  "Preview / Inspection": TableChartIcon,
  Multidimensional: TimelineIcon,
};

const DEFAULT_ICON = TableChartIcon;

export function CategoryIcon({ category, color }) {
  const IconComponent = CATEGORY_ICONS[category] || DEFAULT_ICON;
  return <IconComponent style={{ color, fontSize: 30 }} />;
}
