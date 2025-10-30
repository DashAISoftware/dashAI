import React from "react";
import TableChartIcon from "@mui/icons-material/TableChart";
import BarChartIcon from "@mui/icons-material/BarChart";
import ScatterPlotIcon from "@mui/icons-material/ScatterPlot";
import TimelineIcon from "@mui/icons-material/Timeline";
import FunctionsIcon from "@mui/icons-material/Functions";
import BuildIcon from "@mui/icons-material/Build";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import DnsIcon from "@mui/icons-material/Dns";
import LayersIcon from "@mui/icons-material/Layers";
import FilterListIcon from "@mui/icons-material/FilterList";
import Functions from "@mui/icons-material/Functions";
import CasinoIcon from "@mui/icons-material/Casino";
import ExtensionIcon from "@mui/icons-material/Extension";
import Psychology from "@mui/icons-material/Psychology";

// Explorer category to icon mapping
const EXPLORER_CATEGORY_ICONS = {
  Statistical: FunctionsIcon,
  Distribution: BarChartIcon,
  Relationship: ScatterPlotIcon,
  "Preview Inspection": TableChartIcon,
  Multidimensional: TimelineIcon,
};

// Converter category to icon mapping
const CONVERTER_CATEGORY_ICONS = {
  "Basic Preprocessing": BuildIcon,
  Encoding: DnsIcon,
  "Scaling and Normalization": TrendingUpIcon,
  "Dimensionality Reduction": LayersIcon,
  "Feature Selection": FilterListIcon,
  "Polynomial & Kernel Methods": Functions,
  Sampling: CasinoIcon,
  "Advanced Preprocessing": Psychology,
  "Kernel Approximation": FunctionsIcon,
};

const DEFAULT_ICON = ExtensionIcon;

/**
 * Renders an icon component for a given category.
 *
 * @param {Object} props - Component props.
 * @param {string} props.name - Context name used to select the icon map. When equal to "Converter" the CONVERTER_CATEGORY_ICONS map is used; otherwise EXPLORER_CATEGORY_ICONS is used.
 * @param {string} props.category - Category key used to look up an icon component in the chosen icon map.
 * @param {string} [props.color] - CSS color applied to the rendered icon.
 * @returns {JSX.Element} The selected icon component rendered with inline style { color, fontSize: 30 }.
 *
 * @remarks
 * - Falls back to DEFAULT_ICON if the category key is not found in the selected map.
 * - Depends on CONVERTER_CATEGORY_ICONS, EXPLORER_CATEGORY_ICONS, and DEFAULT_ICON being defined in scope.
 */
export function CategoryIcon({ name, category, color }) {
  const iconMap =
    name === "Converter" ? CONVERTER_CATEGORY_ICONS : EXPLORER_CATEGORY_ICONS;
  const IconComponent = iconMap[category] || DEFAULT_ICON;
  return <IconComponent style={{ color: color ?? "white", fontSize: 30 }} />;
}
