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
import FormSchemaDialog from "../../../components/shared/FormSchemaDialog";
import FormSchemaWithSelectedModel from "../../../components/shared/FormSchemaWithSelectedModel";
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
  const [schemaDialogOpen, setSchemaDialogOpen] = useState(false);

  const {
    modelSchema: retrieverModelSchema,
    defaultValues: retrieverInitialParameters,
    yupSchema: retrieverYupSchema,
    loading: retrieverLoading,
  } = useSchema({ modelName: selectedRetriever?.name });

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

  const fetchRetrievers = async () => {
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
  };

  useEffect(() => {
    fetchRetrievers();
  }, [selectedRetrievalParadigm]);

  const handleRetrievalParadigmChange = (event, newValue) => {
    setSelectedRetrievalParadigm(newValue);
    fetchRetrievers();
  };

  const handleRetrieverSelectionChange = (event, newValue) => {
    setSelectedRetriever(newValue);
    console.log("Selected retriever model:", newValue);
  };

  const handleRetrieverParametersChange = (newParams) => {
    setSelectedRetriever((prev) => ({
      ...prev,
      parameters: newParams,
    }));
    console.log("Updated retriever model parameters:", newParams);
  };

  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"auto"}
    >
      <Typography sx={{ fontSize: "16px", mb: 2 }}>
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
        sx={{ mb: 3 }}
      />

      {selectedRetrievalParadigm && selectedRetrievalParadigm.name === "SparseRetriever" && (
        <Autocomplete
          disablePortal
          options={retrieverOptions}
          getOptionLabel={(option) => option.name}
          value={selectedRetriever}
          onChange={handleRetrieverSelectionChange}
          isOptionEqualToValue={(option, value) => option.name === value?.name}
          renderInput={(params) => <TextField {...params} label="Retriever model" />}
          sx={{ mb: 3 }}
        />
      )}

      {selectedRetriever && (
        <Box width="100%">
          <Typography sx={{ fontSize: "16px", mb: 2 }}>
            Configure retriever model
          </Typography>
          <DataGrid
            autoHeight
            rows={[{ id: 1, name: selectedRetriever.name }]}
            columns={[
              {
                field: 'actions',
                type: 'actions',
                headerName: 'Configure',
                getActions: (params) => [
                  <React.Fragment key="retriever-config-action">
                    <GridActionsCellItem
                      key="edit-button"
                      icon={<SettingsIcon />}
                      label="Edit"
                      onClick={() => setSchemaDialogOpen(true)}
                    />
                    <Dialog
                      open={schemaDialogOpen}
                      onClose={() => setSchemaDialogOpen(false)}
                      PaperProps={{
                        sx: {
                          width: { md: 820 },
                          maxHeight: { lg: 700, xl: "auto" },
                          maxWidth: 2000,
                          transition: "width 0.3s ease, height 0.3s ease",
                        },
                      }}
                    >
                      <FormSchemaContainer>
                        <RetrieverConfigurationStepSubComponent
                          selectedRetriever={selectedRetriever}
                          retrieverInitialParameters={retrieverInitialParameters}
                          schemaDialogOpen={schemaDialogOpen}
                          setSchemaDialogOpen={setSchemaDialogOpen}
                          handleRetrieverParametersChange={handleRetrieverParametersChange}
                        />
                      </FormSchemaContainer>
                    </Dialog>
                  </React.Fragment>
                ],
              },
            ]}
            hideFooter
            disableColumnMenu
            disableColumnSelector
            disableSelectionOnClick
          />
        </Box>
      )}

      {selectedRetriever && selectedRetriever.schema && !selectedRetriever.schema.properties && (
        <Typography sx={{ fontSize: "16px", mb: 2 }}>
          No parameters available for this retriever.
        </Typography>
      )}
    </Box>
  );
}

function RetrieverConfigurationStepSubComponent({
  selectedRetriever,
  retrieverInitialParameters,
  schemaDialogOpen,
  setSchemaDialogOpen,
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
    <>
      <DialogTitle>
        <Box display="flex" alignItems="center">
          <IconButton onClick={() => setSchemaDialogOpen(false)}>
            <ArrowBackOutlined />
          </IconButton>
          <Typography variant="h5" sx={{ ml: 2 }}>
            {`${selectedRetriever.name} configuration`}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={4} sx={{ py: 2 }} transition="ease">
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
              setSchemaDialogOpen(false);
            }}
            setError={setErrorForm}
            onCancel={() => {
              if (properties.length > 0) {
                removeLastProperty();
              } else {
                setSchemaDialogOpen(false);
              }
            }}
          />
        </Stack>
      </DialogContent>
    </>
  );
}