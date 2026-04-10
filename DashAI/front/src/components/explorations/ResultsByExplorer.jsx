import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import { useExplorationsContext, contextDefaults } from "./context";
import { ExplorerStatus } from "../../types/explorer";
import { getComponents } from "../../api/component";

import { Box, Paper } from "@mui/material";
import { Info as DetailsIcon } from "@mui/icons-material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

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
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

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

  const handleShowExplorerDetails = (row) => {
    setExplorerData(row);
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
        id: "actions",
        header: "",
        enableSorting: false,
        enableColumnFilter: false,
        size: 60,
        Cell: ({ row }) => (
          <Box sx={{ display: "flex", gap: 0.5 }}>
            <TooltipedCellItem
              icon={<DetailsIcon />}
              label="Show Explorer details"
              tooltip="Show Explorer details"
              onClick={() => handleShowExplorerDetails(row.original)}
              sx={{ color: "primary.main" }}
            />
          </Box>
        ),
      },
      {
        accessorKey: "name",
        header: "Name",
      },
      {
        id: "type_display_name",
        header: "Type",
        accessorFn: (row) => {
          const explorerType = explorerTypes.find(
            (explorer) => explorer.name === row.exploration_type,
          );
          return explorerType?.metadata.display_name;
        },
      },
      {
        accessorKey: "exploration_type",
        header: "Component Name",
      },
      {
        accessorKey: "status",
        header: "Status Value",
      },
      {
        id: "status_display",
        header: "Status",
        accessorFn: (row) => ExplorerStatus[row.status],
      },
    ];
  }, [handleShowExplorerDetails, explorerTypes]);

  const table = useMaterialReactTable({
    columns,
    data: rows,
    muiTableBodyCellProps: { sx: { whiteSpace: "pre" } },
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: {
      density: "compact",
      columnVisibility: {
        exploration_type: false,
        status: false,
      },
    },
    state: { isLoading: loading },
    enableRowSelection: false,
  });

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
        <MaterialReactTable table={table} />

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
