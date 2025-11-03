import React, { useState, useEffect, useMemo } from "react";
import { Box, Autocomplete, TextField, Typography } from "@mui/material";
import useSchema from "../../../../hooks/useSchema";
import { getChunkingComponents } from "../../../../api/rag";
import FormSchemaEmbedded from "../FormSchemaEmbedded";

export default function ChunkingConfigurationStep({
  chunkingModel,
  setChunkingModel,
  setNextEnabled,
}) {
  const [chunkingOptions, setChunkingOptions] = useState([]);
  const [selectedChunking, setSelectedChunking] = useState(null);
  const { defaultValues } = useSchema({ modelName: selectedChunking?.name });

  // Memoize the initial values to prevent unnecessary re-renders
  const initialValues = useMemo(() => {
    if (chunkingModel?.params && Object.keys(chunkingModel.params).length > 0) {
      return chunkingModel.params;
    }
    return defaultValues || {};
  }, [chunkingModel?.params, defaultValues]);

  useEffect(() => {
    const fetchChunkingModels = async () => {
      const data = await getChunkingComponents();
      setChunkingOptions(data);

      if (chunkingModel?.component) {
        const existing = data.find((c) => c.name === chunkingModel.component);
        if (existing) {
          setSelectedChunking(existing);
        }
      }
    };
    fetchChunkingModels();
  }, [chunkingModel?.component]);

  const isNextEnabled = () => {
    if (!selectedChunking) {
      return false;
    }
    if (!chunkingModel || !chunkingModel.params) {
      return false;
    }

    return Object.keys(chunkingModel.params).every((param) => {
      const value = chunkingModel.params[param];
      return value !== undefined && value !== null && value !== "";
    });
  };

  useEffect(() => {
    const enabled = isNextEnabled();
    setNextEnabled(enabled);
  }, [selectedChunking, chunkingModel]);

  const handleChunkingSelectionChange = (event, newValue) => {
    setSelectedChunking(newValue);
    if (newValue) {
      const isDifferentModel =
        !chunkingModel?.component || chunkingModel.component !== newValue.name;

      const modelData = {
        component: newValue.name,
        params: isDifferentModel
          ? newValue.schema?.properties
            ? getInitialParamsFromSchema(newValue.schema.properties)
            : {}
          : chunkingModel?.params || {},
      };
      setChunkingModel(modelData);
    } else {
      setChunkingModel({ component: "", params: {} });
    }
  };

  const handleParametersSave = (params) => {
    const modelData = {
      component: selectedChunking.name,
      params: params,
    };
    setChunkingModel(modelData);

    const isValid =
      selectedChunking &&
      params &&
      Object.keys(params).every((param) => {
        const value = params[param];
        return value !== undefined && value !== null && value !== "";
      });

    setNextEnabled(isValid);
  };

  function getInitialParamsFromSchema(schemaProperties) {
    if (!schemaProperties) return {};
    return Object.keys(schemaProperties).reduce((acc, key) => {
      acc[key] =
        schemaProperties[key].placeholder !== undefined
          ? schemaProperties[key].placeholder
          : "";
      return acc;
    }, {});
  }

  return (
    <Box
      display="flex"
      height="100%"
      width="100%"
      flexDirection="column"
      justifyContent="flex-start"
      overflow="auto"
    >
      <Typography variant="h6" sx={{ mb: 2 }}>
        Configure Chunking Model
      </Typography>
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
        sx={{ mb: 3 }}
      />
      {selectedChunking && selectedChunking.schema && (
        <FormSchemaEmbedded
          model={selectedChunking.name}
          initialValues={initialValues}
          onFormSubmit={handleParametersSave}
          autoSave={true}
        />
      )}
    </Box>
  );
}
