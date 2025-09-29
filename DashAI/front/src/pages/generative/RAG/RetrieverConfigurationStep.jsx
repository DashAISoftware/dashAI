import React, { 
  useState, 
  useEffect, 
  useCallback, 
  useMemo,
} from "react";
import { 
  Box, 
  Dialog, 
  DialogTitle,
  DialogContent, 
  Autocomplete, 
  TextField, 
  Typography,
  IconButton,
  Stack,

} from "@mui/material";
import ArrowBackOutlined from "@mui/icons-material/ArrowBackOutlined";

import { getRetrieverComponents, getRetrievalParadigm } from "../../../api/rag";
import { useSnackbar } from "notistack";
import useSchema from "../../../hooks/useSchema";

import FormSchemaModelSelect from "../../../components/shared/FormSchemaModelSelect";
import FormSchemaContainer from "../../../components/shared/FormSchemaContainer";
import { useFormSchemaStore } from "../../../contexts/schema";
import FormSchemaBreadScrumbs from "../../../components/shared/FormSchemaBreadScrumbs";
import FormSchema from "../../../components/shared/FormSchema";

import FormSchemaDialog from "../../../components/shared/FormSchemaDialog";

export default function RetrieverConfigurationStep({ setNextEnabled }) {
  const { enqueueSnackbar } = useSnackbar();
  const [retrievalParadigms, setRetrievalParadigms] = useState([]);
  const [selectedRetrievalParadigm, setSelectedRetrievalParadigm] = useState(null);

  const [retrieverOptions, setRetrieverOptions] = useState([]);
  const [selectedRetriever, setSelectedRetriever] = useState(null);
  const [openConfig, setOpenConfig] = useState(false);

  const {defaultValues: retrieverInitialParameters} = useSchema({ modelName: selectedRetriever?.name });

  
  // Fetch paradigms
  const fetchRetrievalParadigms = async () => {
    try {
      const data = await getRetrievalParadigm();
      setRetrievalParadigms(data);
      enqueueSnackbar('Retrieval paradigms loaded successfully!', { variant: 'success' });
    } catch (error) {
      console.error("Error fetching retrieval paradigms:", error);
      enqueueSnackbar('Failed to load retrieval paradigms.', { variant: 'error' });
    }
  };

  useEffect(() => {
    fetchRetrievalParadigms();
  }, []);

  // Fetch retrievers when paradigm changes
  const fetchRetrievers = useCallback(async () => {
    if (!selectedRetrievalParadigm) {
      setRetrieverOptions([]);
      setSelectedRetriever(null);
      return;
    }
    if (selectedRetrievalParadigm.name === "SparseRetriever") {
      const retrievers = await getRetrieverComponents(selectedRetrievalParadigm.name);
      setRetrieverOptions(retrievers);
      setSelectedRetriever(null);
    } else {
      setRetrieverOptions([selectedRetrievalParadigm]);
      setSelectedRetriever(selectedRetrievalParadigm);
    }
  }, [selectedRetrievalParadigm]);

  useEffect(() => {
    fetchRetrievers();
  }, [selectedRetrievalParadigm, fetchRetrievers]);

  // Handle paradigm change
  const handleRetrievalParadigmChange = (event, newValue) => {
    setSelectedRetrievalParadigm(newValue);
    console.log("Selected paradigm:", newValue);
    if (newValue === "SparseRetriever") {
      setSelectedRetriever(null);
    }
    else { 
      setRetrieverOptions([newValue]);
      handleRetrieverSelectionChange(event, newValue);
      setOpenConfig(true);
      setNextEnabled(false);
    }
  };

  // Handle retriever change
  const handleRetrieverSelectionChange = (event, newValue) => {
    console.log("Selected retriever:", newValue);
    setSelectedRetriever(newValue);
    setOpenConfig(true);
    setNextEnabled(false);
    // Optionally reset config if needed
  };

  // Handle config change
  const handleRetrieverParametersSave = (newParams) => {
    setSelectedRetriever((prev) => ({
      ...prev,
      parameters: newParams,
    }));
    setNextEnabled(true);
    setOpenConfig(false);
  };

  // Layout: two columns if retriever selected, else one column
  return (
    <Box
      flex={selectedRetriever ? 1 : 'auto'}
      minWidth={selectedRetriever ? 350 : '100%'}
      maxWidth={selectedRetriever ? 400 : '100%'}
      p={2}
      borderRight={selectedRetriever ? '1px solid #eee' : 'none'}
      display="flex"
      flexDirection="column"
      justifyContent="flex-start"
    >
      <Typography variant="h5" sx={{ mb: 2 }}>
        Select retrieval paradigm
      </Typography>
      <Autocomplete
        disablePortal
        options={retrievalParadigms}
        getOptionLabel={(option) => option.name}
        value={selectedRetrievalParadigm}
        onChange={handleRetrievalParadigmChange}
        isOptionEqualToValue={(option, value) => option.name === value?.name}
        renderInput={(params) => <TextField {...params} label="Retrieval paradigm" />}
        sx={{ mb: 2 }}
      />
      {selectedRetrievalParadigm && selectedRetrievalParadigm.name === "SparseRetriever" && (
        <>
        <Typography variant="h5" sx={{ marginY: 2 }}>
          Select retriever model
        </Typography>
        <Autocomplete
          disablePortal
          options={retrieverOptions}
          getOptionLabel={(option) => option.name}
          value={selectedRetriever}
          onChange={handleRetrieverSelectionChange}
          isOptionEqualToValue={(option, value) => option.name === value?.name}
          renderInput={(params) => <TextField {...params} label="Retriever model" />}
          />
        </>
      )}
      {selectedRetriever && selectedRetriever.schema && !selectedRetriever.schema.properties && (
        <Typography variant="h6" sx={{ mb: 2 }}>
          No parameters available for this retriever.
        </Typography>
      )}

      {selectedRetriever && openConfig && (
        <FormSchemaDialog
          modelToConfigure={selectedRetriever.name}
          open={openConfig}
          setOpen={setOpenConfig}
          onFormSubmit={handleRetrieverParametersSave}
        >
          <FormSchema
            model={selectedRetriever.name}
            initialValues={selectedRetriever.parameters}
            onFormSubmit={handleRetrieverParametersSave}
            onCancel={() => setOpenConfig(false)}
          />
        </FormSchemaDialog>
      )}
  </Box>
);
}
