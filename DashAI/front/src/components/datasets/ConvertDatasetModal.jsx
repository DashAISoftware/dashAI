import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { GridActionsCellItem } from "@mui/x-data-grid";
import { Settings, Help } from "@mui/icons-material";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  Button,
  DialogActions,
  Tooltip,
  Typography,
  IconButton,
  TextField,
  CircularProgress,
} from "@mui/material";
import DatasetSummaryTable from "./DatasetSummaryTable";
import ConverterSelectorModal from "./ConverterSelectorModal";
import ConverterTable from "./ConverterTable";
import { useSnackbar } from "notistack";
import { enqueueConverterJob as enqueueConverterJobRequest } from "../../api/job";
import { startJobQueue as startJobQueueRequest } from "../../api/job";
import {
  saveDatasetConverterList,
  getDatasetConverterList,
} from "../../api/converter";
import { ConverterListStatus } from "../../types/converter";
import { getExperimentsExist } from "../../api/datasets";
import CopyDatasetModal from "./CopyDatasetModal";

/**
 * Modal to modify a dataset by applying a list of converters
 * @param {Object} props
 * @param {number} props.datasetId - ID of the dataset to modify
 */
function ConvertDatasetModal({ datasetId }) {
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  const [targetColumnIndex, setTargetColumnIndex] = useState(null);
  const [convertersToApply, setConvertersToApply] = useState([]);
  const [openCopyModal, setOpenCopyModal] = useState(false);
  const [datasetIdToModify, setDatasetIdToModify] = useState(datasetId);
  const [converterListId, setConverterListId] = useState(null);
  const [converterListStatus, setConverterListStatus] = useState(null);
  const [running, setRunning] = useState(false);

  const handleCloseContent = () => {
    setOpen(false);
  };

  const enqueueConverterJob = async (converterListId) => {
    try {
      await enqueueConverterJobRequest(converterListId, targetColumnIndex);
      enqueueSnackbar("Converter job successfully created.", {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar("Error while trying to enqueue converter job.");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };

  const startJobQueue = async () => {
    try {
      await startJobQueueRequest();
    } catch (error) {
      enqueueSnackbar("Error while trying to start job queue");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };

  const saveAndEnqueueConverterList = async (id) => {
    try {
      // Save the list of converters to apply
      let sequenceOrder = 1;

      const flattenConverterList = convertersToApply.reduce(
        (acc, { name, params, scope }) => {
          // If the converter is a Pipeline, we need to store the steps separately
          if (name === "Pipeline" && params?.steps) {
            acc[name] = {
              params: {
                ...params,
                steps: params.steps.length, // Store the number of steps in the Pipeline
              },
              scope: scope,
              order: sequenceOrder,
            };
            params.steps.forEach((step) => {
              sequenceOrder += 1; // Increase the `order` for each step
              acc[step.name] = {
                params: step.params,
                scope: step.scope,
                order: sequenceOrder,
              };
            });
          } else {
            sequenceOrder += 1; // Increase the `order` for each converter
            acc[name] = {
              params: params,
              scope: scope,
              order: sequenceOrder,
            };
          }

          return acc;
        },
        {},
      );

      const response = await saveDatasetConverterList(id, flattenConverterList);

      const converterListId = response.id;
      setConverterListId(converterListId);

      // Enqueue the converter job using the id of the saved list
      await enqueueConverterJob(converterListId);

      await startJobQueue();

      setRunning(true);
      enqueueSnackbar("Running converter jobs.", {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar("Failed to save converter list: " + error.message, {
        variant: "error",
      });
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };

  const handleSaveConfig = async () => {
    // Check if there are experiments associated with the dataset
    try {
      const hasExperiments = await getExperimentsExist(datasetIdToModify);
      if (hasExperiments) {
        setOpenCopyModal(true);
      } else {
        await saveAndEnqueueConverterList(datasetIdToModify);
      }
    } catch (error) {
      enqueueSnackbar(
        "Error while trying to check if there are experiments associated with the dataset",
        {
          variant: "error",
        },
      );
    }
  };

  const getConverterListStatus = async () => {
    try {
      const convertersFromDB = await getDatasetConverterList(converterListId);
      setConverterListStatus(convertersFromDB.status);

      // Set running to false if status is ERROR or FINISHED
      if (convertersFromDB.status === ConverterListStatus.ERROR) {
        setRunning(false);
        enqueueSnackbar("Converter job failed", {
          variant: "error",
        });
      } else if (convertersFromDB.status === ConverterListStatus.FINISHED) {
        setRunning(false);
        enqueueSnackbar("Dataset successfully modified.", {
          variant: "success",
        });
        setConvertersToApply([]);
        setTargetColumnIndex(null);
      }
    } catch (error) {
      setRunning(false);
      let errorMessage = "Error while checking converter status: ";

      if (error.response?.data?.detail) {
        errorMessage += error.response.data.detail;
      } else if (error.message) {
        errorMessage += error.message;
      } else {
        errorMessage += "Failed to fetch converter status";
      }

      enqueueSnackbar(errorMessage, {
        variant: "error",
      });
      console.error("Error in getConverterListStatus:", error);
    }
  };

  // polling to update the state of the run
  useEffect(() => {
    if (running) {
      const interval = setInterval(() => {
        getConverterListStatus();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [running]);

  return (
    <React.Fragment>
      <Tooltip
        title={<Typography>Modify dataset</Typography>}
        placement="top"
        arrow
      >
        <GridActionsCellItem
          key="converter-component"
          icon={<Settings />}
          label="Modify dataset"
          onClick={() => setOpen(true)}
          sx={{ color: "warning.main" }}
        />
      </Tooltip>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth={"md"}
      >
        <DialogTitle>Modify dataset</DialogTitle>
        <DialogContent dividers>
          {running ? (
            <CircularProgress color="inherit" />
          ) : (
            <Grid
              container
              direction="row"
              justifyContent="space-around"
              alignItems="stretch"
              rowGap={2}
              onClick={(event) => event.stopPropagation()}
            >
              {/* Dataset summary table */}
              <Grid item xs={12}>
                <Typography variant="subtitle1" component="h3" mb={1}>
                  Dataset summary
                </Typography>
              </Grid>
              <DatasetSummaryTable datasetId={datasetIdToModify} />

              {/* Converter selector */}
              <Grid item xs={12} display={"flex"} alignItems={"center"} gap={2}>
                <Grid item xs={6} display={"flex"} alignItems={"center"}>
                  <Typography variant="subtitle1" component="h3" mb={1}>
                    List of converters
                  </Typography>
                  <Tooltip
                    title={`Converters are for modifying the data in a supervised or unsupervised way
    (e.g. by adding, changing, or removing columns, but not by adding or removing rows). The list will be applied following the defined order.`}
                    placement="top"
                  >
                    <IconButton>
                      <Help />
                    </IconButton>
                  </Tooltip>
                  <ConverterSelectorModal
                    setConvertersToApply={setConvertersToApply}
                  />
                </Grid>
                <Grid item xs={6} display={"flex"} alignItems={"center"}>
                  <Typography variant="subtitle2" component="h3" mb={1}>
                    Target column index
                  </Typography>
                  <Tooltip
                    title={`Supervised converters will include this column in their learning process.`}
                    placement="top"
                  >
                    <IconButton>
                      <Help />
                    </IconButton>
                  </Tooltip>
                  <TextField
                    id="target-column-index"
                    label="Index"
                    value={targetColumnIndex}
                    placeholder="1"
                    autoComplete="off"
                    onChange={(event) =>
                      setTargetColumnIndex(event.target.value)
                    }
                    variant="outlined"
                    size="small"
                    required
                    type="number"
                  />
                </Grid>
              </Grid>
              {/* Selected converters table */}
              <ConverterTable
                datasetId={datasetIdToModify}
                convertersToApply={convertersToApply}
                setConvertersToApply={setConvertersToApply}
              />
            </Grid>
          )}
        </DialogContent>
        {/* Actions - Close and Modify */}
        <DialogActions>
          <Button onClick={handleCloseContent}>Close</Button>
          <Button
            onClick={handleSaveConfig}
            autoFocus
            variant="contained"
            color="primary"
            disabled={
              convertersToApply.length === 0 ||
              targetColumnIndex === null ||
              running
            }
          >
            Modify
          </Button>
        </DialogActions>
      </Dialog>
      {/* Modal to make a copy of the dataset */}
      <CopyDatasetModal
        datasetId={datasetIdToModify}
        updateDatasetId={setDatasetIdToModify}
        open={openCopyModal}
        setOpen={setOpenCopyModal}
        modifyDataset={saveAndEnqueueConverterList}
      />
    </React.Fragment>
  );
}

ConvertDatasetModal.propTypes = {
  datasetId: PropTypes.number.isRequired,
};

export default ConvertDatasetModal;
