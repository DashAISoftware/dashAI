import React, { useState, useEffect, useMemo } from "react";
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
import RAGFormSchema from "../components/RAGFormSchema";
import {
  buildDefaultValuesFromSchemaProperties,
  getInitialModelParameters,
} from "../components/ragFormDefaults";
import { getModelFromSubform, getParamsFromSubform } from "../../../../utils/schema";

export default function ChunkingConfigurationStep({
  chunkingModel,
  setChunkingModel,
  setNextEnabled,
}) {
  const [chunkingOptions, setChunkingOptions] = useState([]);
  const [selectedChunking, setSelectedChunking] = useState(null);
  const [error, setError] = useState(null);

  const formInitialValues = useMemo(
    () => {
      const modelName = getModelFromSubform(chunkingModel);
      const params = getParamsFromSubform(chunkingModel) ?? chunkingModel?.params;
      const vals = getInitialModelParameters({
        selectedModel: selectedChunking,
        currentModelName: modelName,
        currentParams: params,
      });
      console.log("[ChunkingConfigStep] formInitialValues:", { 
        modelName, 
        params, 
        selectedChunking: selectedChunking?.name,
        vals
      });
      return vals;
    },
    [selectedChunking, chunkingModel],
  );

  useEffect(() => {
    let isMounted = true;
    const fetchChunkingModels = async () => {
      const data = await getChunkingComponents();
      if (isMounted) {
        setChunkingOptions(data || []);
        console.log("[ChunkingConfigStep] Fetched chunking options:", data);
      }
    };
    fetchChunkingModels();
    return () => {
      isMounted = false;
    };
  }, []);

  // If parent gives a preselected chunking model, sync it
  useEffect(() => {
    if (!chunkingOptions.length) return;
    const modelName = getModelFromSubform(chunkingModel);
    console.log("[ChunkingConfigStep] Syncing selectedChunking:", {
      modelName,
      chunkingModel,
      chunkingOptions: chunkingOptions.map(c => c.name),
    });
    if (modelName) {
      const found = chunkingOptions.find(
        (c) => c.name === modelName,
      );
      if (found) {
        console.log("[ChunkingConfigStep] Found chunking model:", found.name);
        setSelectedChunking(found);
        setNextEnabled(true);
      }
    } else {
      setNextEnabled(false);
    }
  }, [chunkingOptions, chunkingModel]);

  const handleChunkingSelectionChange = (event, newValue) => {
    setSelectedChunking(newValue);
    setError(null);

    if (newValue) {
      setChunkingModel({
        component: newValue.name,
        params: buildDefaultValuesFromSchemaProperties(
          newValue.schema?.properties || {},
        ),
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
          <RAGFormSchema
            key={`chunking-form-${selectedChunking.name}`}
            autoSave
            model={selectedChunking.name}
            initialValues={formInitialValues}
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
