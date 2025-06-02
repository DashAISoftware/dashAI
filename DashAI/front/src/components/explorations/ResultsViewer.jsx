import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import { useExplorationsContext } from "./context";

import { Button, Divider, Grid, Typography } from "@mui/material";

import { useSnackbar } from "notistack";
import { getExplorersByExplorationId } from "../../api/explorer";

import { TIMESTAMP_KEYS } from "../../constants/timestamp";
import TimestampWrapper from "../shared/TimestampWrapper";
import ResultsByExplorer from "./ResultsByExplorer";
import ResultsAll from "./ResultsAll";

const viewModes = {
  ALL: "ALL",
  BY_EXPLORER: "BY_EXPLORER",
};

/**
 * Component to view the results of an exploration. It allows the user to switch between
 * viewing the results by explorer or all explorers.
 * @param {Object} props
 * @param {boolean} props.updateFlag - Flag to update the explorers
 * @param {Function} props.setUpdateFlag - Function to set the update flag
 */
function ResultsViewer({ updateFlag = false, setUpdateFlag = () => {} }) {
  const { enqueueSnackbar } = useSnackbar();
  const { explorationData, setExplorationData } = useExplorationsContext();

  const [viewMode, setViewMode] = useState(viewModes.ALL);
  const [loading, setLoading] = useState(false);

  const handleChangeViewMode = (mode) => {
    setViewMode(mode);
  };

  useEffect(() => {
    if (updateFlag) {
      setLoading(true);
      getExplorersByExplorationId(explorationData.id)
        .then((explorers) => {
          setExplorationData((prev) => ({ ...prev, explorers }));
        })
        .catch((error) => {
          enqueueSnackbar("Error while trying to fetch explorers", {
            variant: "error",
          });
        })
        .finally(() => {
          setLoading(false);
          setUpdateFlag(false);
        });
    }
  }, [updateFlag]);

  return (
    <React.Fragment>
      <Divider flexItem />
      <Grid container direction="column" alignItems="center">
        <Grid item container justifyContent="flex-start" sx={{ mt: 1, mb: 1 }}>
          <Grid item sx={{ ml: 2 }}>
            <Typography variant="body1">
              View all or view by explorer details
            </Typography>
          </Grid>
        </Grid>
        <Grid item sx={{ my: 1 }}>
          <Grid container justifyContent="center">
            <TimestampWrapper
              eventName={TIMESTAMP_KEYS.exploration.viewResults}
            >
              <Button
                variant="contained"
                color={viewMode === viewModes.ALL ? "primary" : "inherit"}
                onClick={() => handleChangeViewMode(viewModes.ALL)}
                style={{
                  border: "2px solid #00bebb",
                  color: viewMode === viewModes.ALL ? "#ffffff" : "#00bebb",
                  borderRadius: "1px",
                }}
              >
                All
              </Button>
            </TimestampWrapper>
            <TimestampWrapper
              eventName={TIMESTAMP_KEYS.exploration.viewResults}
            >
              <Button
                variant="contained"
                color={
                  viewMode === viewModes.BY_EXPLORER ? "primary" : "inherit"
                }
                onClick={() => handleChangeViewMode(viewModes.BY_EXPLORER)}
                style={{
                  border: "2px solid #00bebb",
                  color:
                    viewMode === viewModes.BY_EXPLORER ? "#ffffff" : "#00bebb",
                  borderRadius: "1px",
                }}
              >
                By Explorer
              </Button>
            </TimestampWrapper>
          </Grid>
        </Grid>
      </Grid>

      <Divider flexItem />

      {viewMode === viewModes.BY_EXPLORER && (
        <ResultsByExplorer
          loading={loading}
          updateFlag={updateFlag}
          setUpdateFlag={setUpdateFlag}
        />
      )}

      {viewMode === viewModes.ALL && (
        <ResultsAll updateFlag={updateFlag} setUpdateFlag={setUpdateFlag} />
      )}
    </React.Fragment>
  );
}

ResultsViewer.propTypes = {
  updateFlag: PropTypes.bool,
  setUpdateFlag: PropTypes.func,
};

export default ResultsViewer;
