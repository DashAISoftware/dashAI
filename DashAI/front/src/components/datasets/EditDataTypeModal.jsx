import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";
import { Edit } from "@mui/icons-material";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  Button,
  DialogActions,
  Typography,
  CircularProgress,
  Paper,
  IconButton,
  Tooltip,
} from "@mui/material";
import DatasetSummaryTable from "./DatasetSummaryTable";
import { updateDataset } from "../../api/datasets";

function EditDataTypeModal({ datasetId, updateDatasets }) {
  const [open, setOpen] = useState(false);
  const [columnsSpec, setColumnsSpec] = useState({});
  const [datasetUploaded, setDatasetUploaded] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    if (open) {
      setDatasetUploaded(true);
    }
  }, [columnsSpec, open]);

  const handleClose = () => {
    setOpen(false);
  };

  const handleSave = async () => {
    try {
      await updateDataset(datasetId, { columns: columnsSpec });
      enqueueSnackbar("Dataset updated successfully", { variant: "success" });
      updateDatasets();
      setOpen(false);
    } catch (error) {
      enqueueSnackbar("Error while trying to update the dataset", {
        variant: "error",
      });
      console.error(error);
    }
  };

  return (
    <>
      <Tooltip title="Edit Data Types">
        <span>
          <IconButton
            key="edit-types-button"
            size="small"
            aria-label="Edit Data Types"
            onClick={() => setOpen(true)}
            sx={{ color: "warning.main" }}
          >
            <Edit />
          </IconButton>
        </span>
      </Tooltip>
      <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">
        <DialogTitle>Edit Data Types</DialogTitle>
        <DialogContent onClick={(event) => event.stopPropagation()}>
          <Paper
            variant="outlined"
            sx={{ p: 4, maxHeight: "55vh", overflow: "auto" }}
          >
            <Grid container direction="column" alignItems="center">
              <Grid>
                <Typography variant="subtitle1">Dataset Summary</Typography>
                <Typography
                  variant="caption"
                  component="h3"
                  sx={{ mb: 2, color: "grey" }}
                >
                  Summary of the dataset. You can modify the type by selecting a
                  different value.
                </Typography>
              </Grid>
              <Grid>
                {datasetUploaded ? (
                  <DatasetSummaryTable
                    datasetId={datasetId}
                    isEditable={true}
                    columnsSpec={columnsSpec}
                    setColumnsSpec={setColumnsSpec}
                  />
                ) : (
                  <CircularProgress />
                )}
              </Grid>
            </Grid>
          </Paper>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleSave} variant="contained" color="primary">
            Save and Close
          </Button>
          <Button onClick={handleClose} variant="contained" color="secondary">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

EditDataTypeModal.propTypes = {
  datasetId: PropTypes.number.isRequired,
  updateDatasets: PropTypes.func.isRequired,
};

export default EditDataTypeModal;
