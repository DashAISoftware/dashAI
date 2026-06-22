import React, { useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { ExplorationsProvider } from "../../../components/explorations/context";
import ConfigureExplorersModal from "./ExplorationModal";

const DataExplorationNode = ({
  open,
  onClose,
  onSave,
  savedConfig = null,
  prevNodes = [],
  displayMode = "dialog",
}) => {
  const datasetNode = prevNodes?.find((node) => node?.file_path && node?.id);
  const datasetId = datasetNode?.id ?? null;
  const { enqueueSnackbar } = useSnackbar();

  const hasWarnedRef = useRef(false);
  useEffect(() => {
    if (open && !datasetId) {
      if (!hasWarnedRef.current) {
        enqueueSnackbar("Missing dataset", { variant: "warning" });
        hasWarnedRef.current = true;
      }
      return;
    }
  }, [open, datasetId]);

  const handleClose = () => {
    onClose();
  };

  const handleSave = (explorers) => {
    onSave(explorers);
    onClose();
  };

  if (!open) return null;

  if (!datasetId) {
    return (
      <Box sx={{ p: 1 }}>
        <Typography variant="body2" color="warning.main">
          Missing dataset. Connect a DataSelector node first.
        </Typography>
      </Box>
    );
  }

  return (
    <ExplorationsProvider datasetId={datasetId}>
      <ConfigureExplorersModal
        open={open}
        onClose={handleClose}
        onSave={handleSave}
        savedConfig={savedConfig}
        displayMode={displayMode}
      />
    </ExplorationsProvider>
  );
};

DataExplorationNode.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  savedConfig: PropTypes.object,
  prevNodes: PropTypes.arrayOf(PropTypes.object),
  displayMode: PropTypes.string,
};

export default DataExplorationNode;
