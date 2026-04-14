// columns related to open details of runs
import React from "react";
import { IconButton } from "@mui/material";

export const actionsColumns = (actions) =>
  actions.map((action) => ({
    id: action.title.toLowerCase(),
    header: action.title,
    enableSorting: false,
    enableColumnFilter: false,
    size: 50,
    muiTableHeadCellProps: { align: "center" },
    muiTableBodyCellProps: { align: "center" },
    Cell: ({ row }) => {
      const loading = row.original.status === 1 || row.original.status === 2; // Delivered or Started

      return (
        <IconButton
          onClick={() => action.handleAction(row.original)}
          title={action.title}
          color="primary"
          size="small"
          disabled={
            action.alwaysEnabled
              ? false
              : !action.requiresFinished
                ? loading
                : row.original.status !== 3 // Finished
          }
          loading={action.alwaysEnabled ? false : loading}
        >
          {action.alwaysEnabled || !loading ? <action.Icon /> : null}
        </IconButton>
      );
    },
  }));
