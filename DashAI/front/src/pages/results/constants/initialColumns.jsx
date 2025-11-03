// columns that are common to all runs
import React from "react";
import { styled } from "@mui/material";
import { formatDate } from "../../../utils";

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
      let color;
      switch (params.value) {
        case "Not Started":
          color = "#626262";
          break;
        case "Finished":
          color = "#43A047";
          break;
        case "Running":
          color = "#FFEA00";
          break;
        case "Error":
          color = "#A70909";
          break;
        default:
          break;
      }
      return <StyledCell color={color}>{params.value}</StyledCell>;
    },
  },
  {
    field: "created",
    headerName: "Created",
    type: Date,
    minWidth: 140,
    valueGetter: (value) => formatDate(value),
  },
  {
    field: "last_modified",
    headerName: "Last modified",
    type: Date,
    minWidth: 140,
    valueGetter: (value) => formatDate(value),
  },
  {
    field: "start_time",
    headerName: "Start",
    type: Date,
    minWidth: 140,
    valueGetter: (value) => formatDate(value),
  },
  {
    field: "end_time",
    headerName: "End",
    type: Date,
    minWidth: 140,
    valueGetter: (value) => formatDate(value),
  },
];
