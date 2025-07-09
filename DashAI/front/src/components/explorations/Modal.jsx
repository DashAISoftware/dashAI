import React, { useCallback } from "react";
import PropTypes from "prop-types";

import {
  Dialog,
  DialogTitle,
  DialogContent,
  Grid,
  Typography,
  IconButton,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";

import { useExplorationsContext } from "./context";
import { ExplorationModule } from ".";

/**
 * Component that displays the exploration module content in a modal.
 * It uses the context to get current dataset, exploration and explorer data.
 * @param {object} props
 * @param {boolean} props.open - Flag to open the modal.
 * @param {function} props.onClose - Function to call when the modal is closed.
 */
function ExplorationsModal({
  open,
  onClose = () => {},
  closeOnBackdropClick = true,
}) {
  const { explorationMode, explorationData, explorerData } =
    useExplorationsContext();
  const { dataset_id: datasetId, id: explorationId } = explorationData;
  const { id: explorerId } = explorerData;

  const handleCloseContent = useCallback(
    (_e, reason) => {
      if (!closeOnBackdropClick && reason === "backdropClick") return;
      onClose();
    },
    [onClose],
  );

  return (
    <Dialog
      open={open}
      onClose={handleCloseContent}
      fullWidth
      disableEscapeKeyDown
      maxWidth="lg"
      scroll="paper"
      PaperProps={{
        sx: {
          minHeight: "80vh",
          overflow: "auto",
          maxHeight: "90vh",
        },
      }}
    >
      {explorationMode.showModalTitle && (
        <DialogTitle>
          <Grid
            container
            direction={"row"}
            justifyContent={"space-between"}
            alignItems={"center"}
          >
            {explorationMode.modalTitle && (
              <Grid item>
                {explorationMode.modalTitle}{" "}
                <Typography variant="caption" color="textSecondary">
                  (Dataset ID: {datasetId}
                  {explorationId > 0 && ` | Exploration ID: ${explorationId}`}
                  {explorerId > 0 && ` | Explorer ID: ${explorerId}`})
                </Typography>
              </Grid>
            )}

            <Grid item>
              <IconButton onClick={onClose} color="error">
                <CloseIcon />
              </IconButton>
            </Grid>
          </Grid>
        </DialogTitle>
      )}
      <DialogContent dividers={explorationMode.showModalTitle}>
        <ExplorationModule />
      </DialogContent>
    </Dialog>
  );
}

ExplorationsModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func,
};

export default ExplorationsModal;
