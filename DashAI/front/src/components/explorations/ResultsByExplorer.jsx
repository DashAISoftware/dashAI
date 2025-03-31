import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import { useExplorationsContext, contextDefaults } from "./context";
import { ExplorerStatus } from "../../types/explorer";
import { getComponents } from "../../api/component";

import { Paper } from "@mui/material";
import { Info as DetailsIcon } from "@mui/icons-material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";

import TooltipedCellItem from "../shared/TooltipedCellItem";
import ExplorerDetails from "./explorers/ExplorerDetails";

/**
 * Component that displays explorers in a table format, with actions to show details of each explorer.
 * @param {Object} props
 * @param {boolean} props.loading - Flag to indicate if the component is loading data.
 * @param {boolean} props.updateFlag - Flag to indicate if the component should update.
 * @param {function} props.setUpdateFlag - Function to set the update flag.
 */
function ResultsByExplorer({
  loading = false,
  updateFlag = false,
  setUpdateFlag = () => {},
}) {
  const { explorationData, setExplorerData } = useExplorationsContext();
  const { explorers } = explorationData;

  const [explorerTypes, setExplorerTypes] = useState([]);
  const getExplorerTypes = () => {
    // fetch explorer types
    getComponents({ selectTypes: ["Explorer"] }).then((data) => {
      setExplorerTypes(data);
    });
  };
  useEffect(() => {
    getExplorerTypes();
  }, [explorers]);

  const [rows, setRows] = useState([]);
  const [showExplorerDetails, setShowExplorerDetails] = useState(false);

  const handleShowExplorerDetails = (params) => {
    setExplorerData(params.row);
    setShowExplorerDetails(true);
  };

  const handleHideExplorerDetails = () => {
    setShowExplorerDetails(false);
    setExplorerData((prev) => ({
      ...prev,
      ...contextDefaults.defaultExplorerData,
      exploration_id: prev.exploration_id,
    }));
  };

  useEffect(() => {
    setRows(explorers);
  }, [explorers]);

  const columns = useMemo(() => {
    return [
      {
        field: "actions",
        type: "actions",
        minWidth: 80,
        getActions: (params) => [
          <TooltipedCellItem
            key="details-button"
            icon={<DetailsIcon />}
            label="Show Explorer details"
            tooltip="Show Explorer details"
            onClick={() => handleShowExplorerDetails(params)}
            sx={{ color: "primary.main" }}
          />,
        ],
      },
      {
        field: "name",
        headerName: "Name",
        minWidth: 200,
      },
      {
        field: "type_display_name",
        headerName: "Type",
        minWidth: 200,
        valueGetter: (params) => {
          const explorerType = explorerTypes.find(
            (explorer) => explorer.name === params.row.exploration_type,
          );
          return explorerType?.metadata.display_name;
        },
      },
      {
        field: "exploration_type",
        headerName: "Component Name",
        minWidth: 200,
      },
      {
        field: "status",
        headerName: "Status Value",
        minWidth: 200,
      },
      {
        field: "status_display",
        headerName: "Status",
        minWidth: 200,
        valueGetter: (params) => {
          return ExplorerStatus[params.row.status];
        },
      },
    ];
  }, [handleShowExplorerDetails, explorerTypes]);

  return (
    <React.Fragment>
      <Paper
        sx={{
          display: "flex",
          flexDirection: "column",
          px: 3,
          py: 2,
          width: "100%",
        }}
        // solves a mui problem related to putting datagrid inside another datagrid
        onClick={(event) => {
          event.target = document.body;
        }}
      >
        <DataGrid
          slots={{
            toolbar: GridToolbar,
          }}
          slotProps={{
            toolbar: {
              showQuickFilter: true,
            },
          }}
          loading={loading}
          rows={rows}
          columns={columns}
          autoHeight
          disableRowSelectionOnClick
          density="compact"
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 5,
              },
            },
            filter: {
              // filterModel: {
              //   items: [
              //     {
              //       field: "status_display",
              //       operator: "contains",
              //       value: ExplorerStatus[ExplorerStatus.FINISHED],
              //     },
              //   ],
              // },
            },
            columns: {
              columnVisibilityModel: {
                exploration_type: false,
                status: false,
              },
            },
          }}
          pageSizeOptions={[5, 10, 20]}
        />

        {showExplorerDetails && (
          <ExplorerDetails
            handleClose={() => {
              handleHideExplorerDetails();
            }}
            updateFlag={updateFlag}
            setUpdateFlag={setUpdateFlag}
          />
        )}
      </Paper>
    </React.Fragment>
  );
}

ResultsByExplorer.propTypes = {
  loading: PropTypes.bool,
  updateFlag: PropTypes.bool,
  setUpdateFlag: PropTypes.func,
};

export default ResultsByExplorer;
