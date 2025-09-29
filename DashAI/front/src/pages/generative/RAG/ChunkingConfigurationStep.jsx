import React, { useState, useEffect, useMemo } from "react";
import { Box, Autocomplete, TextField, Typography } from "@mui/material";
import useSchema from "../../../hooks/useSchema";
import { getChunkingComponents } from "../../../api/rag";
import FormSchemaEmbedded from "./FormSchemaEmbedded";

export default function ChunkingConfigurationStep({ chunkingModel, setChunkingModel, setNextEnabled }) {
  const [chunkingOptions, setChunkingOptions] = useState([]);
  const [selectedChunking, setSelectedChunking] = useState(null);
  const { defaultValues } = useSchema({ modelName: selectedChunking?.name });

  // Memoize the initial values to prevent unnecessary re-renders
  const initialValues = useMemo(() => {
    if (chunkingModel?.parameters && Object.keys(chunkingModel.parameters).length > 0) {
      return chunkingModel.parameters;
    }
    return defaultValues || {};
  }, [chunkingModel?.parameters, defaultValues]);

  useEffect(() => {
    const fetchChunkingModels = async () => {
      const data = await getChunkingComponents();
      setChunkingOptions(data);
      if (chunkingModel?.name) {
        const existing = data.find(c => c.name === chunkingModel.name);
        if (existing) setSelectedChunking(existing);
      }
    };
    fetchChunkingModels();
  }, [chunkingModel?.name]);

  const isNextEnabled = () => {
    if (!selectedChunking) {
      return false;
    }
    if (!chunkingModel || !chunkingModel.parameters) {
      
      return false; // Ensure parameters are required
    }
    
    return Object.keys(chunkingModel.parameters).every(param => {
      const value = chunkingModel.parameters[param];
      return value !== undefined && value !== null && value !== "";
    });
  };

  useEffect(() => {
    setNextEnabled(isNextEnabled());
  }, [selectedChunking, chunkingModel, setNextEnabled]);


  const handleChunkingSelectionChange = (event, newValue) => {
    setSelectedChunking(newValue);
    if (newValue) {
      setChunkingModel({
        name: newValue.name,
        parameters: newValue.schema?.properties ? getInitialParamsFromSchema(newValue.schema.properties) : {},
      });
    } else {
      setChunkingModel({ name: "", parameters: {} });
    }
  };

  const handleParametersSave = (params) => {
    setChunkingModel({
      name: selectedChunking.name,
      parameters: params,
    });
    setNextEnabled(isNextEnabled());
    console.log("Saved:", chunkingModel);
    console.log("Next enabled:", isNextEnabled());
  };

  function getInitialParamsFromSchema(schemaProperties) {
    if (!schemaProperties) return {};
    return Object.keys(schemaProperties).reduce((acc, key) => {
      acc[key] = schemaProperties[key].placeholder !== undefined
        ? schemaProperties[key].placeholder
        : "";
      return acc;
    }, {});
  }

  return (
    <Box display="flex" height="100%" width="100%" flexDirection="column" justifyContent="flex-start" overflow="auto">
      <Typography variant="h6" sx={{ mb: 2 }}>
        Configure Chunking Model
      </Typography>
      <Autocomplete
        disablePortal
        options={chunkingOptions}
        getOptionLabel={option => option.name}
        value={selectedChunking}
        onChange={handleChunkingSelectionChange}
        isOptionEqualToValue={(option, value) => option.name === value?.name}
        renderInput={params => <TextField {...params} label="Chunking Model" />}
        sx={{ mb: 3 }}
      />
      {selectedChunking && selectedChunking.schema && (
        <FormSchemaEmbedded
            model={selectedChunking.name}
            initialValues={initialValues}
            onFormSubmit={handleParametersSave}
            onCancel={() => setSelectedChunking(null)}
          />
      )}
    </Box>
  );
}
