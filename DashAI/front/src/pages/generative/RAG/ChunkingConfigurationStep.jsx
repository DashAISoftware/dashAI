import React, { useState, useEffect, useCallback } from "react";
import { Box, Autocomplete, TextField, Typography } from "@mui/material";
import useSchema from "../../../hooks/useSchema";
import { getChunkingComponents } from "../../../api/rag";
import FormSchemaContainer from "../../../components/shared/FormSchemaContainer";
import FormSchema from "../../../components/shared/FormSchema";

export default function ChunkingConfigurationStep({ chunkingModel, setChunkingModel, setNextEnabled }) {
  const [chunkingOptions, setChunkingOptions] = useState([]);
  const [selectedChunking, setSelectedChunking] = useState(null);
  const { defaultValues } = useSchema({ modelName: selectedChunking?.name });

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

  useEffect(() => {
    setNextEnabled(!!selectedChunking);
  }, [selectedChunking, setNextEnabled]);

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

  const handleParametersChange = (params) => {
    setChunkingModel({
      name: selectedChunking.name,
      parameters: params,
    });
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
        <FormSchemaContainer>
          <FormSchema
            model={selectedChunking.name}
            initialValues={chunkingModel?.parameters || defaultValues}
            onFormSubmit={handleParametersChange}
            onCancel={() => setSelectedChunking(null)}
          />
        </FormSchemaContainer>
      )}
    </Box>
  );
}
