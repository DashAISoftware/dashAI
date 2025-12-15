import React from "react";
import * as Icons from "@mui/icons-material";

const DEFAULT_ICON = Icons.Science;

/**
 * Renders an icon component for a given model.
 *
 * @param {Object} props - Component props.
 * @param {string} props.iconName - Icon name from Material-UI (comes from backend metadata.icon).
 * @param {string} [props.color] - CSS color applied to the rendered icon.
 * @returns {JSX.Element} The selected icon component.
 *
 * @remarks
 * - Falls back to DEFAULT_ICON (Science) if the icon name is not found.
 * - The iconName should match a Material-UI icon name (e.g., "Forest", "Timeline", "ScatterPlot").
 */
export function ModelIcon({ iconName, color }) {
  const IconComponent = Icons[iconName] || DEFAULT_ICON;
  return <IconComponent style={{ color: color ?? "white", fontSize: 24 }} />;
}
