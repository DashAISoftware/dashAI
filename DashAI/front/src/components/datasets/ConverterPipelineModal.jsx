import React, { useState } from "react";
import { GridActionsCellItem } from "@mui/x-data-grid";
import {
  Box,
  IconButton,
  Typography,
  Button,
  ButtonGroup,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Stack,
  DialogContentText,
  MenuItem,
  Tooltip,
} from "@mui/material";
import { ArrowBackOutlined, Cable } from "@mui/icons-material";
import PropTypes from 'prop-types';

/**
 * Modal to manage the pipeline of converters
 * @param {Object} props
 * @param {Array} props.converters - List of selected converters to apply
 * @param {Function} props.setConvertersToApply - Function to update the list of converters to apply
 * @param {Array} props.existingPipelines - List of existing pipelines
 * @param {Object} props.converterToAdd - Converter to add to the pipeline
 */
const ConverterPipelineModal = ({
  converters,
  setConvertersToApply,
  existingPipelines,
  converterToAdd,
}) => {
  const [open, setOpen] = useState(false);
  const [selectedPipeline, setSelectedPipeline] = useState({
    name: "",
    id: "",
    scope: {
      columns: [],
      rows: [],
    },
    params: {
      steps: [],
    },
  });
  const assignedPipeline = existingPipelines.find(
    (pipeline) =>
      pipeline.params.steps.some((converter) => converter.id === converterToAdd.id),
  );
  const alreadyInPipeline = assignedPipeline !== undefined;

  const handleOnChange = (event) => {
    console.log(event.target.value);
    if (event.target.value === "Remove from pipeline") {
      setSelectedPipeline({
        name: "Remove from pipeline",
        id: "Remove from pipeline",
        scope: {
          columns: [],
          rows: [],
        },
        params: {
          steps: [],
        },
      });
      return;
    }
    const pipeline = existingPipelines.find((p) => p.id === event.target.value);
    setSelectedPipeline(pipeline);
  };

  const handleAddToExistingPipeline = () => {
    // We move the convertToAdd from convertersToApply to selectedPipeline.params.steps
    let updatedConverters = converters.filter(
      (converter) => converter.id !== converterToAdd.id,
    );
    let pipelineIndex = updatedConverters.findIndex(
      (converter) => converter.id === selectedPipeline.id,
    );
    if (pipelineIndex !== -1) {
      updatedConverters[pipelineIndex] = {
        ...updatedConverters[pipelineIndex],
        params: {
          ...updatedConverters[pipelineIndex].params,
          steps: [
            ...updatedConverters[pipelineIndex].params.steps,
            converterToAdd,
          ],
        },
      };
    }
    setConvertersToApply(updatedConverters);
  };

  const moveConverterFromPipelineToSequence = () => {
    // Find the index of the pipeline that contains the converter to remove
    const pipelineIndex = converters.findIndex((converter) =>
      converter.params.steps.some((step) => step.id === converterToAdd.id),
    );

    if (pipelineIndex === -1) {
      return;
    }

    // Create the updated converters array
    const updatedConverters = [
      ...converters.slice(0, pipelineIndex + 1),
      converterToAdd,
      ...converters.slice(pipelineIndex + 1),
    ];

    // Update the pipeline by removing the converter from its steps
    updatedConverters[pipelineIndex] = {
      ...updatedConverters[pipelineIndex],
      params: {
        ...updatedConverters[pipelineIndex].params,
        steps: updatedConverters[pipelineIndex].params.steps.filter(
          (step) => step.id !== converterToAdd.id,
        ),
      },
    };

    setConvertersToApply(updatedConverters);
  };

  const handleOnSave = () => {
    // If the selected item is Remove from pipeline, we remove the converter from the pipeline
    if (selectedPipeline.id === "Remove from pipeline") {
      moveConverterFromPipelineToSequence();
      setOpen(false);
      return;
    }

    // Add the converter to the selected pipeline if not already in it
    if (!alreadyInPipeline) {
      handleAddToExistingPipeline();
    }
    setOpen(false);
  };

  return (
    <React.Fragment>
      <Tooltip
        title={<Typography>Manage pipeline</Typography>}
        placement="top"
        arrow
      >
        <GridActionsCellItem
          key="manage-pipeline-button"
          icon={<Cable />}
          label="Manage pipeline"
          onClick={() => setOpen(true)}
        >
          Manage pipeline
        </GridActionsCellItem>
      </Tooltip>
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <IconButton onClick={() => setOpen(false)}>
              <ArrowBackOutlined />
            </IconButton>
            <Typography variant="h5" sx={{ ml: 2 }}>
              Manage pipeline
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={4} sx={{ py: 2 }} transition="ease">
            <DialogContentText>
              A Pipeline applies a sequence of converters to preprocess data,
              passing the output of one converter to the next, with its scope
              defined by the first converter.
            </DialogContentText>
            <TextField
              select
              value={selectedPipeline.id}
              onChange={handleOnChange}
              fullWidth
              label="Select pipeline"
            >
              {existingPipelines.map((pipeline, index) => (
                <MenuItem key={pipeline.id} value={pipeline.id}>
                  {pipeline.name} {index + 1}
                </MenuItem>
              ))}
              {alreadyInPipeline && (
                <MenuItem value="Remove from pipeline">
                  Remove from pipeline
                </MenuItem>
              )}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <ButtonGroup>
            <Button onClick={() => setOpen(false)}>Back</Button>
            <Button variant="contained" onClick={handleOnSave}>
              Save
            </Button>
          </ButtonGroup>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
};

ConverterPipelineModal.propTypes = {
  converters: PropTypes.arrayOf(PropTypes.object).isRequired,
  setConvertersToApply: PropTypes.func.isRequired,
  existingPipelines: PropTypes.arrayOf(PropTypes.object).isRequired,
  converterToAdd: PropTypes.object.isRequired,
};

export default ConverterPipelineModal;
