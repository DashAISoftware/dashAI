import { useState, useEffect, useCallback } from "react";
import { 
  Box, 
  Dialog, 
  DialogTitle,
  DialogContent, 
  Autocomplete, 
  TextField, 
  Typography,
  IconButton,

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
import FormSchemaContainer from "../../../components/shared/FormSchemaContainer";
import FormSchemaHeader from "../../../components/shared/FormSchemaHeader";

export default function RetrieverConfigurationStep({ setNextEnabled }) {
  const { enqueueSnackbar } = useSnackbar();
  const [retrievalParadigms, setRetrievalParadigms] = useState([]);
  const [selectedRetrievalParadigm, setSelectedRetrievalParadigm] = useState(null);

  const [retrieverOptions, setRetrieverOptions] = useState([]);
  const [selectedRetriever, setSelectedRetriever] = useState(null);
  const [retrieverParamsSchema, setRetrieverParamsSchema] = useState(null);
  const {
    modelSchema: retrieverModelSchema,
    defaultValues: retrieverInitialParameters,
    yupSchema: retrieverYupSchema,
    loading: retrieverLoading,
  } = useSchema({ modelName: selectedRetriever?.name });


  const [schemaDialogOpen, setSchemaDialogOpen] = useState(false);
  const handleSchemaDialogClose = () => setSchemaDialogOpen(false);

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
    fetchRetrievers()
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
  }

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
            columns={
              [ 
              {
              field: 'actions',
              type: 'actions',
              headerName: 'Configure',
              getActions: (params) => [
                <>
                  <GridActionsCellItem
                    key="edit-button"
                    icon={<SettingsIcon />}
                    label="Edit"
                    onClick={() => setSchemaDialogOpen(true)}
                  />
                   <Dialog
                      open={schemaDialogOpen}
                      onClose={handleSchemaDialogClose}
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
                        <DialogTitle>
                          <Box display="flex" alignItems="center">
                            <IconButton onClick={handleSchemaDialogClose}>
                              <ArrowBackOutlined />
                            </IconButton>
                            <Typography variant="h5" sx={{ ml: 2 }}>
                              {`${selectedRetriever.name} configuration`}
                            </Typography>
                          </Box>
                        </DialogTitle>
                        <DialogContent>

                          <FormSchemaWithSelectedModel
                            modelToConfigure={selectedRetriever.name}
                            initialValues={retrieverInitialParameters}
                            onFormSubmit={(values) => {
                              handleRetrieverParametersChange(values);
                              setSchemaDialogOpen(false);
                            }}
                            onCancel={() => setSchemaDialogOpen(false)}
                            />
                      </DialogContent>
                    </FormSchemaContainer>
                  </Dialog>
                </>
              ],
            }]}
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