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
 * Modal to manage the chain of converters
 * @param {Object} props
 * @param {Array} props.converters - List of selected converters to apply
 * @param {Function} props.setConvertersToApply - Function to update the list of converters to apply
 * @param {Array} props.existingChains - List of existing chains
 * @param {Object} props.converterToAdd - Converter to add to the chain
 */
const ConverterChainModal = ({
  converters,
  setConvertersToApply,
  existingChains,
  converterToAdd,
}) => {
  const [open, setOpen] = useState(false);
  const [selectedChain, setSelectedChain] = useState({
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
  const assignedChain = existingChains.find(
    (chain) =>
      chain.params.steps.some((converter) => converter.id === converterToAdd.id),
  );
  const alreadyInChain = assignedChain !== undefined;

  const handleOnChange = (event) => {
    if (event.target.value === "Remove from chain") {
      setSelectedChain({
        name: "Remove from chain",
        id: "Remove from chain",
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
    const chain = existingChains.find((c) => c.id === event.target.value);
    setSelectedChain(chain);
  };

  const handleAddToExistingChain = () => {
    // We move the convertToAdd from convertersToApply to selectedChain.params.steps
    let updatedConverters = converters.filter(
      (converter) => converter.id !== converterToAdd.id,
    );
    let chainIndex = updatedConverters.findIndex(
      (converter) => converter.id === selectedChain.id,
    );
    if (chainIndex !== -1) {
      updatedConverters[chainIndex] = {
        ...updatedConverters[chainIndex],
        params: {
          ...updatedConverters[chainIndex].params,
          steps: [
            ...updatedConverters[chainIndex].params.steps,
            converterToAdd,
          ],
        },
      };
    }
    setConvertersToApply(updatedConverters);
  };

  const moveConverterFromChainToSequence = () => {
    // Find the index of the chain that contains the converter to remove
    const chainIndex = converters.findIndex((converter) =>
      converter.params.steps.some((step) => step.id === converterToAdd.id),
    );

    if (chainIndex === -1) {
      return;
    }

    // Create the updated converters array
    const updatedConverters = [
      ...converters.slice(0, chainIndex + 1),
      converterToAdd,
      ...converters.slice(chainIndex + 1),
    ];

    // Update the chain by removing the converter from its steps
    updatedConverters[chainIndex] = {
      ...updatedConverters[chainIndex],
      params: {
        ...updatedConverters[chainIndex].params,
        steps: updatedConverters[chainIndex].params.steps.filter(
          (step) => step.id !== converterToAdd.id,
        ),
      },
    };

    setConvertersToApply(updatedConverters);
  };

  const handleOnSave = () => {
    // If the selected item is Remove from chain, we remove the converter from the chain
    if (selectedChain.id === "Remove from chain") {
      moveConverterFromChainToSequence();
      setOpen(false);
      return;
    }

    // Add the converter to the selected chain if not already in it
    if (!alreadyInChain) {
      handleAddToExistingChain();
    }
    setOpen(false);
  };

  return (
    <React.Fragment>
      <Tooltip
        title={<Typography>Manage chain</Typography>}
        placement="top"
        arrow
      >
        <GridActionsCellItem
          key="manage-chain-button"
          icon={<Cable />}
          label="Manage chain"
          onClick={() => setOpen(true)}
        >
          Manage chain
        </GridActionsCellItem>
      </Tooltip>
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <IconButton onClick={() => setOpen(false)}>
              <ArrowBackOutlined />
            </IconButton>
            <Typography variant="h5" sx={{ ml: 2 }}>
              Manage chain
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={4} sx={{ py: 2 }} transition="ease">
            <DialogContentText>
              A Chain applies a sequence of converters to preprocess data,
              passing the output of one converter to the next, with its scope
              defined by the first converter.
            </DialogContentText>
            <TextField
              select
              value={selectedChain.id}
              onChange={handleOnChange}
              fullWidth
              label="Select chain"
            >
              {existingChains.map((chain, index) => (
                <MenuItem key={chain.id} value={chain.id}>
                  {chain.name} {index + 1}
                </MenuItem>
              ))}
              {alreadyInChain && (
                <MenuItem value="Remove from chain">
                  Remove from chain
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

ConverterChainModal.propTypes = {
  converters: PropTypes.arrayOf(PropTypes.object).isRequired,
  setConvertersToApply: PropTypes.func.isRequired,
  existingChains: PropTypes.arrayOf(PropTypes.object).isRequired,
  converterToAdd: PropTypes.object.isRequired,
};

export default ConverterChainModal;
