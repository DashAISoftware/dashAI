import React, { useEffect, useState, useCallback } from "react";
import {
  Button,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { Help, AddCircleOutline as AddIcon } from "@mui/icons-material";
import ItemSelectorWithInfo from "../../custom/ItemSelectorWithInfo";

import { getComponents as getComponentsRequest } from "../../../api/component";
import useSchema from "../../../hooks/useSchema";
import uuid from "react-uuid";
import PropTypes from "prop-types";

/**
 * Modal to select and add a converter to the list of converters to apply
 * @param {Object} props
 * @param {Function} props.setConvertersToApply - Function to update the list of converters to apply
 */
const ConverterSelectorModal = ({ setConvertersToApply }) => {
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [converters, setConverters] = useState([]);

  const [selectedConverter, setSelectedConverter] = useState({});

  const { defaultValues: defaultParameters } = useSchema({
    modelName: selectedConverter.name,
  });

  const getListOfConverters = useCallback(async () => {
    setLoading(true);
    try {
      const converters = await getComponentsRequest({
        selectTypes: ["Converter"],
      });
      setConverters(converters);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain list of converters");
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
  }, []);

  // Fetch converters on mount
  useEffect(() => {
    getListOfConverters();
  }, []);

  const handleAddConverter = () => {
    setOpen(false);
    setConvertersToApply((prev) => [
      ...prev,
      {
        id: uuid(),
        name: selectedConverter.name,
        schema: selectedConverter.schema,
        params: defaultParameters,
        scope: {
          columns: [],
          rows: [],
        },
      },
    ]);
    setSelectedConverter({});
  };

  const handleOnClose = () => {
    setOpen(false);
  };

  return (
    <React.Fragment>
      {/* Open modal to edit new converter */}
      <Button
        onClick={() => setOpen(true)}
        autoFocus
        variant="outlined"
        color="primary"
        key="edit-button"
        startIcon={<AddIcon />}
      >
        Add
      </Button>
      {/* Modal to select a converter */}
      <Dialog open={open} onClose={handleOnClose} fullWidth maxWidth={"xl"}>
        {/* New converter to apply */}
        <DialogTitle> Select a converter to add </DialogTitle>
        <DialogContent dividers>
          <Grid
            container
            direction="row"
            justifyContent="space-around"
            alignItems="stretch"
            spacing={2}
          >
            <Grid item xs={12}>
              <Grid container spacing={1}>
                {/* Converter list and description */}
                {!loading ? (
                  <ItemSelectorWithInfo
                    itemsList={converters}
                    selectedItem={selectedConverter}
                    setSelectedItem={setSelectedConverter}
                  />
                ) : (
                  <CircularProgress color="inherit" />
                )}
              </Grid>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleOnClose}>Close</Button>
          <Button
            variant="contained"
            onClick={handleAddConverter}
            disabled={
              !selectedConverter || Object.keys(selectedConverter).length === 0
            }
          >
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
};

ConverterSelectorModal.propTypes = {
  setConvertersToApply: PropTypes.func.isRequired,
};

export default ConverterSelectorModal;
