import { useState, useEffect, useCallback } from "react";
import { Box, Autocomplete, TextField, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import EditModelDialog from "../../../components/experiments/EditModelDialog";
import { getRetrieverComponents, getRetrievalParadigm } from "../../../api/rag";
import { useSnackbar } from "notistack";
import useSchema from "../../../hooks/useSchema";

export default function RetrieverConfigurationStep({ setNextEnabled }) {
  const { enqueueSnackbar } = useSnackbar();
  const [retrievalParadigms, setRetrievalParadigms] = useState([]);
  const [selectedRetrievalParadigm, setSelectedRetrievalParadigm] = useState(null);

  const [retrieverOptions, setRetrieverOptions] = useState([]);
  const [selectedRetriever, setSelectedRetriever] = useState(null);
  const [retrieverInitialParameters, setRetrieverInitialParameters] = useState({});
  const [retrieverParamsSchema, setRetrieverParamsSchema] = useState(null);

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

      // For non-Sparse paradigms, only set retriever if schema and schema.properties exist
      if (selectedRetrievalParadigm.schema && selectedRetrievalParadigm.schema.properties) {
        setRetrieverOptions([selectedRetrievalParadigm]);
        setSelectedRetriever(selectedRetrievalParadigm);
      } else {
        setRetrieverOptions([]);
        setSelectedRetriever(null);
      }
  };

  useEffect(() => {
    fetchRetrievers();
  }, [selectedRetrievalParadigm]);

  const handleRetrievalParadigmChange = (event, newValue) => {
    setSelectedRetrievalParadigm(newValue);
    setSelectedRetriever(null);
  };

  const handleRetrieverSelectionChange = (event, newValue) => {
    setSelectedRetriever(newValue);
    setRetrieverInitialParameters(useSchema({ modelName: newValue?.name }));
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

      {selectedRetriever && (
        <Box width="100%">
          <Typography sx={{ fontSize: "16px", mb: 2 }}>
            Configure retriever model
          </Typography>
          <DataGrid
            autoHeight
            rows={[{ id: 1, name: selectedRetriever.name }]}
            columns={[{
              field: 'name',
              headerName: 'Retriever',
              flex: 1,
            }, {
              field: 'actions',
              type: 'actions',
              headerName: 'Configure',
              getActions: (params) => [
                <EditModelDialog
                  key="edit"
                  modelToConfigure={selectedRetriever.name}
                  updateParameters={handleRetrieverParametersChange}
                  paramsInitialValues={retrieverInitialParameters}
                />
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