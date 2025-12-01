// columns related to open details of runs
import React from "react";
import { GridActionsCellItem } from "@mui/x-data-grid";
import { IconButton } from "@mui/material";
import { getRunStatus } from "../../../utils/runStatus";

export const actionsColumns = (actions) =>
  actions.map((action) => ({
    field: action.title.toLowerCase(),
    headerName: action.title,
    sortable: false,
    filterable: false,
    disableColumnMenu: true,
    align: "center",
    headerAlign: "center",
    minWidth: 50,
    renderCell: (params) => (
      <IconButton
        onClick={() =>
          action.useRowData
            ? action.handleAction(params.id, params.row.name)
            : action.handleAction(params.id)
        }
        title={action.title}
        color="primary"
        size="small"
        disabled={params.row.status !== "Finished"}
      >
        <action.Icon />
      </IconButton>
    ),
  }));
