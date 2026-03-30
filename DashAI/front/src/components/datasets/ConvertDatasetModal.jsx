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
import { LoadingButton } from "@mui/material";
import DatasetSummaryTable from "./DatasetSummaryTable";
import ConverterSelectorModal from "./converterModals/ConverterSelectorModal";
import ConverterTable from "./ConverterTable";
import { useSnackbar } from "notistack";
import { enqueueConverterJob as enqueueConverterJobRequest } from "../../api/job";
import { saveConverter, getDatasetConverter } from "../../api/converter";
import { ConverterStatus } from "../../types/converter";
import { getModelSessionsExist } from "../../api/datasets";
import CopyDatasetModal from "./converterModals/CopyDatasetModal";
import ConverterClassColumnModal from "./converterModals/ConverterClassColumnModal";
import TooltipedCellItem from "../shared/TooltipedCellItem";

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
  const [converterId, setConverterId] = useState(null);
  const [converterStatus, setConverterStatus] = useState(null);
  const [running, setRunning] = useState(false);

  const handleCloseContent = () => {
    setOpen(false);
  };

  const enqueueConverterJob = async (converterId) => {
    try {
      await enqueueConverterJobRequest(converterId, targetColumnIndex);
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

  const saveAndEnqueueConverter = async (id) => {
    try {
      // Save the list of converters to apply
      const flattenConverter = convertersToApply.reduce(
        (acc, { name, params, scope }, index) => {
          acc[name] = {
            params: params,
            scope: scope,
            order: index + 1,
          };

          return acc;
        },
        {},
      );

      const response = await saveConverter(id, flattenConverter);

      const converterId = response.id;
      setConverterId(converterId);

      // Enqueue the converter job using the id of the saved list
      await enqueueConverterJob(converterId);

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
      const hasExperiments = await getModelSessionsExist(datasetIdToModify);
      if (hasExperiments) {
        setOpenCopyModal(true);
      } else {
        await saveAndEnqueueConverter(datasetIdToModify);
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

  const getConverterStatus = async () => {
    try {
      const convertersFromDB = await getDatasetConverter(converterId);
      setConverterStatus(convertersFromDB.status);

      // Set running to false if status is ERROR or FINISHED
      if (convertersFromDB.status === ConverterStatus.ERROR) {
        setRunning(false);
        enqueueSnackbar("Converter job failed", {
          variant: "error",
        });
      } else if (convertersFromDB.status === ConverterStatus.FINISHED) {
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
      console.error("Error in getConverterStatus:", error);
    }
  };

  // polling to update the state of the run
  useEffect(() => {
    if (running) {
      const interval = setInterval(() => {
        getConverterStatus();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [running]);

  return (
    <React.Fragment>
      <TooltipedCellItem
        key="converter-component"
        icon={<Settings />}
        label="Modify dataset"
        tooltip="Modify dataset"
        onClick={() => setOpen(true)}
        sx={{ color: "warning.main" }}
      />
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
              <Grid size={{ xs: 12 }}>
                <Typography variant="subtitle1" component="h3" mb={1}>
                  Dataset summary
                </Typography>
              </Grid>
              <DatasetSummaryTable datasetId={datasetIdToModify} />

              {/* Converter selector */}
              <Grid
                size={{ xs: 12 }}
                display={"flex"}
                alignItems={"center"}
                gap={2}
              >
                <Grid size={{ xs: 6 }} display={"flex"} alignItems={"center"}>
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
                <Grid size={{ xs: 6 }} display={"flex"} alignItems={"center"}>
                  <Typography variant="subtitle2" component="h3" mb={1}>
                    Class/Target column index
                  </Typography>
                  <Tooltip
                    title={`Supervised converters will include this column in their learning process.`}
                    placement="top"
                  >
                    <IconButton>
                      <Help />
                    </IconButton>
                  </Tooltip>
                  <ConverterClassColumnModal
                    datasetId={datasetIdToModify}
                    classColumnInitialValue={targetColumnIndex}
                    updateClassColumn={setTargetColumnIndex}
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
          <LoadingButton
            onClick={handleSaveConfig}
            autoFocus
            variant="contained"
            color="primary"
            disabled={
              convertersToApply.length === 0 ||
              targetColumnIndex === null ||
              running
            }
            loading={running}
          >
            Modify
          </LoadingButton>
        </DialogActions>
      </Dialog>
      {/* Modal to make a copy of the dataset */}
      <CopyDatasetModal
        datasetId={datasetIdToModify}
        updateDatasetId={setDatasetIdToModify}
        open={openCopyModal}
        setOpen={setOpenCopyModal}
        modifyDataset={saveAndEnqueueConverter}
      />
    </React.Fragment>
  );
}

ConvertDatasetModal.propTypes = {
  datasetId: PropTypes.number.isRequired,
};

export default ConvertDatasetModal;
