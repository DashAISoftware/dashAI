import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import { Box, ButtonGroup, Paper, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";

import {
  PlayArrow as PlayArrowIcon,
  Check as CheckIcon,
} from "@mui/icons-material";

import { LoadingButton } from "@mui/material";
import { useSnackbar } from "notistack";

import { getComponents } from "../../api/component";
import { ExplorerStatus } from "../../types/explorer";
import { getExplorersByExplorationId as getExplorersRequest } from "../../api/explorer";
import { useExplorationsContext } from "./context";

import { formatDate } from "../../utils";
import { useTranslation } from "react-i18next";

/**
 * Component to run explorers from an exploration. It uses context to get the exploration data.
 * @param {Object} props
 * @param {Function} props.handleCloseDialog - Function to close the dialog
 * @param {Boolean} props.updateFlag - Flag to update the explorers
 */
function ExplorationRunner({
  handleCloseDialog = () => {},
  updateFlag = false,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { explorationData } = useExplorationsContext();
  const { id: explorationId, explorers } = explorationData;
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState(explorers);

  const toMRT = (ids) =>
    Object.fromEntries(ids.map((id) => [String(id), true]));
  const fromMRT = (sel) =>
    Object.keys(sel)
      .filter((k) => sel[k])
      .map(Number);

  const [rowSelection, setRowSelection] = useState(
    toMRT(explorers.map((explorer) => explorer.id)),
  ); // Select all explorers by default

  const rowSelectionModel = fromMRT(rowSelection);

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

  const [running, setRunning] = useState(false);
  const [finishedRunning, setFinishedRunning] = useState(true);
  const [launchedJobs, setLaunchedJobs] = useState(false);

  const launchJob = async (explorerId) => {
    return enqueueJobRequest(explorerId);
  };

  const submitExecutions = async (notify = true) => {
    return Promise.all(
      rowSelectionModel.map((explorerId) => launchJob(explorerId)),
    ).then(() => {
      if (notify) {
        enqueueSnackbar("Explorers started successfully", {
          variant: "success",
        });
      }
      setLaunchedJobs(true);
    });
  };

  const handleExecuteExplorers = async () => {
    setRunning(true);
    // send runs to the job queue
    submitExecutions()
      .then(() => {
        getExplorers();
      })
      .catch((error) => {
        enqueueSnackbar("Error while trying to start explorers", {
          variant: "error",
        });
      });
  };

  const getExplorers = async () => {
    setLoading(true);
    getExplorersRequest(explorationId)
      .then((explorers) => {
        setRows(explorers);
      })
      .catch((error) => {
        enqueueSnackbar("Error while trying to fetch explorers", {
          variant: "error",
        });
      })
      .finally(() => {
        setLoading(false);
      });
  };

  // update state of explorer jobs
  useEffect(() => {
    if (rows.length > 0) {
      let isAnyExplorerRunning = rows.some(
        (explorer) =>
          explorer.status === ExplorerStatus.DELIVERED ||
          explorer.status === ExplorerStatus.STARTED,
      );
      let areAllFinished = rows.every(
        (explorer) => explorer.status === ExplorerStatus.FINISHED,
      );

      // notify when all explorers are finished and previously some were running
      if (launchedJobs && areAllFinished) {
        enqueueSnackbar("All Explorers finished successfully", {
          variant: "success",
        });
      }

      setRunning(isAnyExplorerRunning);
      setFinishedRunning(areAllFinished);
    }
  }, [rows]);

  // polling to update the state of the runs
  useEffect(() => {
    if (updateFlag) {
      getExplorers();
    }

    if (running) {
      setLaunchedJobs(true);
      const interval = setInterval(() => {
        getExplorers();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [running, updateFlag]);

  const columns = useMemo(
    () => [
      {
        accessorKey: "id",
        header: "ID",
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
      {
        id: "last_modified",
        header: "Last Modified",
        accessorFn: (row) => formatDate(row.last_modified),
      },
    ],
    [explorerTypes],
  );

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
        id: false,
        exploration_type: false,
        status: false,
      },
      sorting: [{ id: "last_modified", desc: true }],
    },
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    state: { rowSelection, isLoading: loading },
    getRowId: (row) => String(row.id),
  });

  return (
    <Box
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: 4,
      }}
    >
      <Paper
        sx={{ display: "flex", flexDirection: "column", px: 6, py: 4 }}
        // solves a mui problem related to putting datagrid inside another datagrid
        onClick={(event) => {
          event.target = document.body;
        }}
      >
        <Typography variant="subtitle1" component="h3" sx={{ pb: 2 }}>
          Select explorers to run
        </Typography>
        <MaterialReactTable table={table} />
      </Paper>

      <ButtonGroup size="large" sx={{ justifyContent: "flex-end" }}>
        <LoadingButton
          variant={"contained"}
          loading={running}
          endIcon={finishedRunning ? <CheckIcon /> : <PlayArrowIcon />}
          onClick={
            finishedRunning ? () => handleCloseDialog() : handleExecuteExplorers
          }
          disabled={!finishedRunning && rowSelectionModel.length === 0}
          color={finishedRunning ? "success" : "primary"}
        >
          {finishedRunning ? "Finish" : "Start"}
        </LoadingButton>

        {!running && finishedRunning && (
          <LoadingButton
            variant="contained"
            loading={running}
            endIcon={<PlayArrowIcon />}
            onClick={handleExecuteExplorers}
            disabled={rowSelectionModel.length === 0}
          >
            Re Run
          </LoadingButton>
        )}
      </ButtonGroup>
    </Box>
  );
}

ExplorationRunner.propTypes = {
  handleCloseDialog: PropTypes.func,
  updateFlag: PropTypes.bool,
};

export default ExplorationRunner;
