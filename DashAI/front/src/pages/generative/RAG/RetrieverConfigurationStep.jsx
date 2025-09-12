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

import { DataGrid } from "@mui/x-data-grid";
import { getRetrieverComponents, getRetrievalParadigm } from "../../../api/rag";
import { useSnackbar } from "notistack";
import useSchema from "../../../hooks/useSchema";
import SettingsIcon from "@mui/icons-material/Settings";
import { GridActionsCellItem } from "@mui/x-data-grid";
import FormSchemaModelSelect from "../../../components/shared/FormSchemaModelSelect";
import FormSchemaContainer from "../../../components/shared/FormSchemaContainer";
import { useFormSchemaStore } from "../../../contexts/schema";
import FormSchemaBreadScrumbs from "../../../components/shared/FormSchemaBreadScrumbs";
import FormSchema from "../../../components/shared/FormSchema";



export default function RetrieverConfigurationStep({ setNextEnabled }) {
  const { enqueueSnackbar } = useSnackbar();
  const [retrievalParadigms, setRetrievalParadigms] = useState([]);
  const [selectedRetrievalParadigm, setSelectedRetrievalParadigm] = useState(null);

  const [retrieverOptions, setRetrieverOptions] = useState([]);
  const [selectedRetriever, setSelectedRetriever] = useState(null);

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
    setSelectedRetriever(null); // Reset retriever selection
  };

  // Handle retriever change
  const handleRetrieverSelectionChange = (event, newValue) => {
    setSelectedRetriever(newValue);
    // Optionally reset config if needed
  };

  // Handle config change
  const handleRetrieverParametersChange = (newParams) => {
    setSelectedRetriever((prev) => ({
      ...prev,
      parameters: newParams,
    }));
    setNextEnabled(true);
  };

  // Layout: two columns if retriever selected, else one column
  return (
    <Box display="flex" height="100%" width="100%" flexDirection="row" overflow="auto">
      {/* Left column: paradigm/model selection */}
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
      </Box>

      {/* Right column: configuration, only if retriever selected */}
      {selectedRetriever && (
        <Box flex={2} minWidth={400} p={2} display="flex" flexDirection="column">
          <FormSchemaContainer>
            <ModelConfigurationSubcomponent
              selectedRetriever={selectedRetriever}
              retrieverInitialParameters={retrieverInitialParameters}
              handleRetrieverParametersChange={handleRetrieverParametersChange}
            />
          </FormSchemaContainer>
        </Box>
      )}
    </Box>
  );
}

function ModelConfigurationSubcomponent({
  selectedRetriever,
  retrieverInitialParameters,
  handleRetrieverParametersChange,
}) {
  const {
    formValues,
    properties,
    propertyData,
    valuesByProperties,
    removeLastProperty,
    setErrorForm,
  } = useFormSchemaStore();

  const [selectedModel, setSelectedModel] = useState(
    selectedRetriever?.name || propertyData?.model,
  );

  const selectedProperty = Boolean(propertyData?.selected);

  const defaultValues = useMemo(() => {
    if (selectedProperty) {
      if (propertyData.params) {
        return propertyData.params;
      } else return null;
    }
    return retrieverInitialParameters ?? valuesByProperties;
  }, [selectedModel, propertyData.params]);

  useEffect(() => {
    if (propertyData.model) {
      setSelectedModel(propertyData.model);
    } else {
      setSelectedModel(selectedRetriever?.name);
    }
  }, [propertyData.model, propertyData.params, selectedRetriever?.name]);

  return (
    <Stack spacing={4} sx={{ py: 2 }} transition="ease">
      <Box display="flex" alignItems="center">
        <ArrowBackOutlined />
        <Typography variant="h6" sx={{ ml: 2 }}>
          {`${selectedRetriever.name} configuration`}
        </Typography>
      </Box>
      {console.log("propertyData:", propertyData)}
      {Boolean(propertyData?.parent) && (
        <>
          <FormSchemaBreadScrumbs />
          <FormSchemaModelSelect
            parent={propertyData.parent}
            selectedModel={selectedModel}
            onChange={setSelectedModel}
          />
        </>
      )}
      <FormSchema
        model={selectedModel}
        initialValues={defaultValues}
        onFormSubmit={() => {
          handleRetrieverParametersChange(formValues);
        }}
        setError={setErrorForm}
        onCancel={() => {
          if (properties.length > 0) {
            removeLastProperty();
          }
        }}
      />
    </Stack>
  );
}