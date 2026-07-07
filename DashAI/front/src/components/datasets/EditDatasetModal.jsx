import React, { useState } from "react";
import PropTypes from "prop-types";
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
import { updateDataset as updateDatasetRequest } from "../../api/datasets";
import { useSnackbar } from "notistack";
import TooltipedCellItem from "../shared/TooltipedCellItem";

function EditDatasetModal({ datasetId, name, updateDatasets }) {
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  const [datasetName, setDatasetName] = useState(name);

  const editDataset = async () => {
    try {
      await updateDatasetRequest(datasetId, { name: datasetName });
      enqueueSnackbar("Dataset updated successfully", {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar("Error while trying to update the dataset");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };

  const handleSaveConfig = () => {
    editDataset();
    updateDatasets();
    setOpen(false);
  };

  return (
    <React.Fragment>
      <TooltipedCellItem
        key="edit-dataset-button"
        icon={<EditIcon />}
        label="Edit dataset"
        tooltip="Edit dataset"
        onClick={() => setOpen(true)}
        sx={{ color: "warning.main" }}
      />
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth={"md"}
      >
        <DialogTitle>Edit dataset</DialogTitle>
        <DialogContent>
          <Grid
            container
            direction="row"
            justifyContent="space-around"
            alignItems="stretch"
            spacing={4}
          >
            {/* New name field */}
            <Grid size={{ xs: 12 }}>
              <Typography variant="subtitle1" component="h3" sx={{ mb: 6 }}>
                Enter a new name for your dataset
              </Typography>

              <TextField
                id="dataset-name-input"
                label="Dataset Name"
                value={datasetName}
                autoComplete="off"
                fullWidth
                onChange={(event) => setDatasetName(event.target.value)}
                sx={{ mb: 4 }}
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

EditDatasetModal.propTypes = {
  datasetId: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  updateDatasets: PropTypes.func.isRequired,
};

export default EditDatasetModal;
