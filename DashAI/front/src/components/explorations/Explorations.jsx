import React, { useState } from "react";
import uuid from "react-uuid";

import { Button, Stack, Box, Typography } from "@mui/material";
import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
  ChevronLeft as BackIcon,
} from "@mui/icons-material";

import { useSnackbar } from "notistack";
import {
  useExplorationsContext,
  explorationModes,
  contextDefaults,
} from "./context";
import {
  ExplorationsTable,
  ExplorationEditor,
  ExplorationRunner,
  ExplorationResultsViewer,
} from "./";
import { getExplorersByExplorationId } from "../../api/explorer";

/**
 * Main component of the Explorations module.
 * Requires the use of the ExplorationsContext.
 * It is responsible for rendering the different views of the module.
 * It handles launching the creation, editing, running and visualization of explorations.
 */
function Explorations() {
  const {
    explorationMode,
    setExplorationMode,
    explorationData,
    setExplorationData,
    setExplorerData,
    setRefreshFlag,
  } = useExplorationsContext();
  const { dataset_id } = explorationData;
  const { enqueueSnackbar } = useSnackbar();

  const [updateFlag, setUpdateFlag] = useState(false);

  const handleCreateExploration = () => {
    setExplorationData((prev) => ({ ...prev, id: uuid() }));
    setExplorationMode(explorationModes.EXPLORATION_CREATE);
  };

  const handleBack = () => {
    setExplorationData((prev) => ({
      ...contextDefaults.defaultExplorationData,
      dataset_id: prev.dataset_id,
    }));
    setExplorerData((prev) => ({
      ...contextDefaults.defaultExplorerData,
      exploration_id: prev.exploration_id,
    }));
    setExplorationMode(contextDefaults.defaultExplorationMode);
    handleReload();
  };

  const handleReload = () => {
    setUpdateFlag(true);
    setRefreshFlag(true);
  };

  const fetchExplorers = async (explorationId) => {
    return await getExplorersByExplorationId(explorationId)
      .then((data) => {
        return data;
      })
      .catch((error) => {
        enqueueSnackbar("Error while trying to fetch explorers", {
          variant: "error",
        });
        return [];
      });
  };

  const handleSelectExploration = (data) => {
    fetchExplorers(data.id).then((explorers) => {
      setExplorationData((prev) => ({ ...prev, ...data, explorers }));
      setExplorationMode(explorationModes.EXPLORATION_EDIT);
    });
  };

  const handleRunExploration = (data) => {
    fetchExplorers(data.id).then((explorers) => {
      setExplorationData((prev) => ({ ...prev, ...data, explorers }));
      setExplorationMode(explorationModes.EXPLORATION_RUN);
    });
  };

  const handleViewExplorationResults = (data) => {
    fetchExplorers(data.id).then((explorers) => {
      setExplorationData((prev) => ({ ...prev, ...data, explorers }));
      setExplorationMode(explorationModes.EXPLORATION_VISUALIZE);
    });
  };

  return (
    <React.Fragment>
      <Stack direction="row" alignItems="center" spacing={2} pl={2} pr={2}>
        {/* Show back button */}
        {explorationMode.backButton && (
          <Button variant="text" onClick={handleBack} startIcon={<BackIcon />}>
            Back
          </Button>
        )}

        {/* Show titles if they exist */}
        {explorationMode.title && (
          <Box sx={{ flexGrow: 1, textAlign: "start" }}>
            <Typography variant="h6" component="div">
              {explorationMode.title}
            </Typography>

            {explorationMode.body && (
              <Typography variant="body1" component="div">
                {explorationMode.body}
              </Typography>
            )}
          </Box>
        )}

        {/* Show creator */}
        {explorationMode.creatorButton && (
          <Button
            variant="contained"
            onClick={handleCreateExploration}
            startIcon={<AddIcon />}
          >
            Create
          </Button>
        )}

        {/* Show reloader */}
        {explorationMode.reloaderButton && (
          <Button
            variant="contained"
            onClick={handleReload}
            endIcon={<UpdateIcon />}
          >
            Update
          </Button>
        )}
      </Stack>

      <Box
        sx={{
          overflowY: "auto",
          overflowX: "auto",
          mt: 2,
          mb: 2,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: 1,
        }}
      >
        {explorationMode === explorationModes.EXPLORATION_LIST && (
          <ExplorationsTable
            updateTableFlag={updateFlag}
            setUpdateTableFlag={setUpdateFlag}
            datasetId={dataset_id}
            onExplorationSelect={handleSelectExploration}
            onExplorationRun={handleRunExploration}
            onViewExplorationResults={handleViewExplorationResults}
          />
        )}

        {explorationMode === explorationModes.EXPLORATION_CREATE && (
          <ExplorationEditor handleCloseDialog={handleBack} />
        )}

        {explorationMode === explorationModes.EXPLORATION_EDIT && (
          <ExplorationEditor handleCloseDialog={handleBack} />
        )}

        {explorationMode === explorationModes.EXPLORATION_RUN && (
          <ExplorationRunner
            handleCloseDialog={handleBack}
            updateFlag={updateFlag}
          />
        )}

        {explorationMode === explorationModes.EXPLORATION_VISUALIZE && (
          <ExplorationResultsViewer
            updateFlag={updateFlag}
            setUpdateFlag={setUpdateFlag}
          />
        )}
      </Box>
    </React.Fragment>
  );
}

export default Explorations;
