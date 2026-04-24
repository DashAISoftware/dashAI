// columns that are common to all runs
import React from "react";
import { styled, useTheme } from "@mui/material";
import { getColorByStatus } from "../../../utils";
import { Translation } from "react-i18next";
import { getRunStatus } from "../../../utils/runStatus";

// style for the cells in the initial columns
const StyledCell = styled("div")(({ theme, color }) => ({
  display: "inline-block",
  padding: theme.spacing(0.5),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: color,
}));

// Component for status cell to properly use theme hook
const StatusCell = ({ value }) => {
  const theme = useTheme();
  const color = getColorByStatus(value, theme);
  return (
    <StyledCell color={color}>
      <Translation>{(t, { i18n }) => getRunStatus(value, t)}</Translation>
    </StyledCell>
  );
};

export const initialColumns = [
  {
    accessorKey: "name",
    header: "Name",
    minSize: 150,
  },
  {
    accessorKey: "model_name",
    header: "Model",
    minSize: 200,
    Cell: ({ cell }) => {
      const value = cell.getValue();
      return (
        <StyledCell color={value?.color ?? "#535353ff"}>
          {value?.display_name ?? value?.name ?? value}
        </StyledCell>
      );
    },
  },
  {
    accessorKey: "status",
    header: "Status",
    minSize: 100,
    Cell: ({ cell }) => <StatusCell value={cell.getValue()} />,
  },
];
