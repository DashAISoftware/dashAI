import React, { useState, useEffect } from "react";
import {
  Box,
  Autocomplete,
  TextField,
  Typography,
  Stack,
  DialogContentText,
} from "@mui/material";
import PropTypes from "prop-types";
import { getChunkingComponents } from "../../../../api/rag";
import FormSchemaLayout from "../../../../components/shared/FormSchemaLayout";
import FormSchema from "../../../../components/shared/FormSchema";

export default function ChunkingConfigurationStep({
  chunkingModel,
  setChunkingModel,
  setNextEnabled,
}) {
  const [chunkingOptions, setChunkingOptions] = useState([]);
  const [selectedChunking, setSelectedChunking] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const fetchChunkingModels = async () => {
      const data = await getChunkingComponents();
      if (isMounted) setChunkingOptions(data || []);
    };
    fetchChunkingModels();
    return () => {
      isMounted = false;
    };
  }, []);

  // If parent gives a preselected chunking model, sync it
  useEffect(() => {
    if (!chunkingOptions.length) return;
    if (chunkingModel?.component) {
      const found = chunkingOptions.find(
        (c) => c.name === chunkingModel.component,
      );
      if (found) setSelectedChunking(found);
    }
    // Enable next when there is a selection
    setNextEnabled(!!chunkingModel?.component);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chunkingOptions, chunkingModel?.component]);

  const handleChunkingSelectionChange = (event, newValue) => {
    setSelectedChunking(newValue);
    setError(null);

    if (newValue) {
      // Set initial params using placeholders if available
      const initialParams = Object.keys(
        newValue.schema?.properties || {},
      ).reduce((acc, k) => {
        acc[k] = newValue.schema.properties[k].placeholder ?? "";
        return acc;
      }, {});

      const existingParams = chunkingModel?.params;
      const shouldUseInitialParams =
        !existingParams || Object.keys(existingParams).length === 0;

      setChunkingModel({
        component: newValue.name,
        params: shouldUseInitialParams ? initialParams : existingParams,
      });
      setNextEnabled(true);
    } else {
      setChunkingModel({ component: "", params: {} });
      setNextEnabled(false);
    }
  };

  const handleFormSubmit = (values) => {
    // Generic validation for any chunking model with chunk_size and chunk_overlap
    if (
      values.chunk_size !== undefined &&
      values.chunk_overlap !== undefined &&
      values.chunk_overlap >= values.chunk_size
    ) {
      const errorMsg =
        "chunk_overlap must be less than chunk_size. " +
        `Got chunk_overlap=${values.chunk_overlap} and chunk_size=${values.chunk_size}`;
      setError(errorMsg);
      setNextEnabled(false);
      return;
    }

    setError(null);
    setChunkingModel({
      component: selectedChunking.name,
      params: values,
    });
    setNextEnabled(true);
  };

  return (
    <Stack spacing={3} sx={{ height: "100%" }}>
      <DialogContentText>
        <Typography sx={{ fontSize: 16 }}>Configure Chunking Model</Typography>
      </DialogContentText>

      <Autocomplete
        disablePortal
        options={chunkingOptions}
        getOptionLabel={(option) => option.name}
        value={selectedChunking}
        onChange={handleChunkingSelectionChange}
        isOptionEqualToValue={(option, value) => option.name === value?.name}
        renderInput={(params) => (
          <TextField {...params} label="Chunking Model" />
        )}
      />

      {error && (
        <Typography variant="body2" color="error" sx={{ px: 1 }}>
          {error}
        </Typography>
      )}

      {selectedChunking && (
        <FormSchemaLayout>
          <FormSchema
            autoSave
            model={selectedChunking.name}
            initialValues={
              chunkingModel?.params &&
              Object.keys(chunkingModel.params).length > 0
                ? chunkingModel.params
                : Object.keys(selectedChunking.schema?.properties || {}).reduce(
                    (acc, k) => {
                      acc[k] =
                        selectedChunking.schema.properties[k].placeholder ?? "";
                      return acc;
                    },
                    {},
                  )
            }
            onFormSubmit={handleFormSubmit}
            setError={(err) => {
              if (err) {
                console.error("FormSchema error:", err);
                setError(err?.message || "Validation error");
                setNextEnabled(false);
              }
            }}
          />
        </FormSchemaLayout>
      )}
    </Stack>
  );
}

ChunkingConfigurationStep.propTypes = {
  chunkingModel: PropTypes.object,
  setChunkingModel: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func,
};
