import React, { useState } from "react";
import PropTypes from "prop-types";
import { GridActionsCellItem } from "@mui/x-data-grid";
import EditIcon from "@mui/icons-material/Edit";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  TextField,
  Typography,
} from "@mui/material";
import { rename_prediction as renamePredictionRequest } from "../../api/predict";
import { useSnackbar } from "notistack";

function EditPredictionModal({ predictName, updatePredictions }) {
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [newPredictName, setPredictName] = useState("");

  const editPrediction = async () => {
    setLoading(true);
    try {
      await renamePredictionRequest(predictName, newPredictName);
      updatePredictions();
      enqueueSnackbar("Prediction updated successfully", {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar("Error while trying to update the prediction");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = () => {
    editPrediction();
    setPredictName("");
    setOpen(false);
  };

  return (
    <React.Fragment>
      <GridActionsCellItem
        key="edit-button"
        icon={<EditIcon />}
        label="Edit"
        onClick={() => setOpen(true)}
        sx={{ color: "warning.main" }}
      />
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth={"md"}
      >
        <DialogTitle>Edit prediction</DialogTitle>
        <DialogContent>
          <Grid
            container
            direction="row"
            justifyContent="space-around"
            alignItems="stretch"
            spacing={2}
          >
            {/* New name field */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
                Enter a new name for your prediction file
              </Typography>

              <TextField
                id="prediction-name-input"
                label="Prediction Name"
                value={newPredictName}
                autoComplete="off"
                fullWidth
                onChange={(event) => setPredictName(event.target.value)}
                sx={{ mb: 2 }}
              />
            </Grid>
          </Grid>
        </DialogContent>

        {/* Actions - Save */}
        <DialogActions>
          <Button
            onClick={handleSaveConfig}
            autoFocus
            variant="contained"
            color="primary"
            disabled={false}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}

EditPredictionModal.propTypes = {
  predictName: PropTypes.string.isRequired,
  updatePredictions: PropTypes.func.isRequired,
};

export default EditPredictionModal;
