import React, { useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";
import { ExplorationsProvider } from "../../../components/explorations/context";
import ConfigureExplorersModal from "./ExplorationModal";

const DataExplorationNode = ({
  open,
  onClose,
  onSave,
  savedConfig = null,
  prevNodes = [],
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

  return (
    <>
      {open && datasetId && (
        <ExplorationsProvider datasetId={datasetId}>
          <ConfigureExplorersModal
            open={open}
            onClose={handleClose}
            onSave={handleSave}
            savedConfig={savedConfig}
          />
        </ExplorationsProvider>
      )}
    </>
  );
};

DataExplorationNode.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  savedConfig: PropTypes.object,
  prevNodes: PropTypes.arrayOf(PropTypes.object),
};

export default DataExplorationNode;
