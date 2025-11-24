// columns related to open details of runs
import React, { act } from "react";
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
    renderCell: (params) => {
      const loading =
        params.row.status === "Started" || params.row.status === "Delivered";

      return (
        <IconButton
          onClick={() => action.handleAction(params.id)}
          title={action.title}
          color="primary"
          size="small"
          disabled={
            !action.requiresFinished
              ? loading
              : params.row.status !== "Finished"
          }
          loading={loading}
        >
          {loading ? null : <action.Icon />}
        </IconButton>
      );
    },
  }));
