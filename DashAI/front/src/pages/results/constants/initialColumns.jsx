// columns that are common to all runs
import React from "react";
import { styled, useTheme } from "@mui/material";
import { formatDate, getColorByStatus } from "../../../utils";

// style for the cells in the initial columns
const StyledCell = styled("div")(({ theme, color }) => ({
  display: "inline-block",
  padding: theme.spacing(0.5),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: color,
}));

export const initialColumns = [
  {
    field: "name",
    headerName: "Name",
    minWidth: 150,
  },
  {
    field: "model_name",
    headerName: "Model",
    minWidth: 200,
    renderCell: (params) => {
      return (
        <StyledCell color={params.value.color ?? "#535353ff"}>
          {params.value.display_name ?? params.value.name}
        </StyledCell>
      );
    },
  },
  {
    field: "status",
    headerName: "Status",
    minWidth: 100,
    renderCell: (params) => {
      // Using a render function to access theme through hook
      const StatusCell = () => {
        const theme = useTheme();
        const color = getColorByStatus(params.value, theme);
        return <StyledCell color={color}>{params.value}</StyledCell>;
      };
      return <StatusCell />;
    },
  },
  // {
  //   field: "created",
  //   headerName: "Created",
  //   type: Date,
  //   minWidth: 140,
  //   valueGetter: (value) => formatDate(value),
  // },
  // {
  //   field: "last_modified",
  //   headerName: "Last modified",
  //   type: Date,
  //   minWidth: 140,
  //   valueGetter: (value) => formatDate(value),
  // },
  // {
  //   field: "start_time",
  //   headerName: "Start",
  //   type: Date,
  //   minWidth: 140,
  //   valueGetter: (value) => formatDate(value),
  // },
  // {
  //   field: "end_time",
  //   headerName: "End",
  //   type: Date,
  //   minWidth: 140,
  //   valueGetter: (value) => formatDate(value),
  // },
];
