import { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { Box, Autocomplete, TextField, Typography } from "@mui/material";

import {
  getRetrieverComponents,
  getRetrievalParadigm,
} from "../../../../api/rag";
import { useSnackbar } from "notistack";
import useSchema from "../../../../hooks/useSchema";

import FormSchema from "../../../../components/shared/FormSchema";
import FormSchemaContainer from "../../../../components/shared/FormSchemaContainer";

export default function RetrieverConfigurationStep({
  retrieverModel,
  setRetrieverModel,
  setNextEnabled,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [retrievalParadigms, setRetrievalParadigms] = useState([]);
  const [selectedRetrievalParadigm, setSelectedRetrievalParadigm] =
    useState(null);

  const [retrieverOptions, setRetrieverOptions] = useState([]);
  const [selectedRetriever, setSelectedRetriever] = useState(null);
  const [openConfig, setOpenConfig] = useState(false);

  const { defaultValues: retrieverInitialParameters } = useSchema({
    modelName: selectedRetriever?.name,
  });
  const fetchRetrievalParadigms = async () => {
    try {
      const data = await getRetrievalParadigm();
      setRetrievalParadigms(data);

      if (retrieverModel?.component) {
        const directParadigm = data.find(
          (paradigm) => paradigm.name === retrieverModel.component,
        );
        if (directParadigm) {
          setSelectedRetrievalParadigm(directParadigm);
          // For DenseRetriever, set it as both paradigm and retriever
          if (directParadigm.name !== "SparseRetriever") {
            setSelectedRetriever(directParadigm);
            setOpenConfig(true);
            setNextEnabled(true);
          }
        } else {
          const sparseParadigm = data.find(
            (paradigm) => paradigm.name === "SparseRetriever",
          );
          if (sparseParadigm) {
            setSelectedRetrievalParadigm(sparseParadigm);
          }
        }
      }

      enqueueSnackbar("Retrieval paradigms loaded successfully!", {
        variant: "success",
      });
    } catch (error) {
      console.error("Error fetching retrieval paradigms:", error);
      enqueueSnackbar("Failed to load retrieval paradigms.", {
        variant: "error",
      });
    }
  };

  useEffect(() => {
    fetchRetrievalParadigms();
  }, [retrieverModel?.component]);

  // Fetch retrievers when paradigm changes
  const fetchRetrievers = useCallback(async () => {
    if (!selectedRetrievalParadigm) {
      setRetrieverOptions([]);
      setSelectedRetriever(null);
      return;
    }
    if (selectedRetrievalParadigm.name === "SparseRetriever") {
      const retrievers = await getRetrieverComponents(
        selectedRetrievalParadigm.name,
      );
      setRetrieverOptions(retrievers);

      if (retrieverModel?.component) {
        const existingRetriever = retrievers.find(
          (r) => r.name === retrieverModel.component,
        );
        if (existingRetriever) {
          setSelectedRetriever(existingRetriever);
          setOpenConfig(true);
          setNextEnabled(true);
        } else {
          setSelectedRetriever(null);
        }
      } else {
        setSelectedRetriever(null);
      }
    } else {
      setRetrieverOptions([selectedRetrievalParadigm]);
      setSelectedRetriever(selectedRetrievalParadigm);
    }
  }, [selectedRetrievalParadigm, retrieverModel?.component]);

  useEffect(() => {
    fetchRetrievers();
  }, [selectedRetrievalParadigm, fetchRetrievers]);

  const handleRetrievalParadigmChange = (event, newValue) => {
    setSelectedRetrievalParadigm(newValue);
    if (newValue?.name === "SparseRetriever") {
      setSelectedRetriever(null);
      setOpenConfig(false);
      setNextEnabled(false);
    } else if (newValue) {
      setRetrieverOptions([newValue]);
      handleRetrieverSelectionChange(event, newValue);
    } else {
      setSelectedRetriever(null);
      setOpenConfig(false);
      setNextEnabled(false);
    }
  };

  // Handle retriever change
  const handleRetrieverSelectionChange = (event, newValue) => {
    setSelectedRetriever(newValue);
    if (newValue) {
      setOpenConfig(true);
      setNextEnabled(true);
    } else {
      setOpenConfig(false);
      setNextEnabled(false);
    }
  };

  const handleRetrieverParametersSave = (newParams) => {
    const updatedRetriever = {
      ...selectedRetriever,
      parameters: newParams,
    };
    setSelectedRetriever(updatedRetriever);

    setRetrieverModel({
      component: selectedRetriever.name,
      params: newParams,
    });

    setNextEnabled(true);
  };

  return (
    <Box
      p={2}
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
        renderInput={(params) => (
          <TextField {...params} label="Retrieval paradigm" />
        )}
        sx={{ mb: 2 }}
      />
      {selectedRetrievalParadigm &&
        selectedRetrievalParadigm.name === "SparseRetriever" && (
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
              isOptionEqualToValue={(option, value) =>
                option.name === value?.name
              }
              renderInput={(params) => (
                <TextField sx={{ mb: 3 }} {...params} label="Retriever model" />
              )}
            />
          </>
        )}
      {selectedRetriever &&
        selectedRetriever.schema &&
        !selectedRetriever.schema.properties && (
          <Typography variant="h6" sx={{ mb: 2 }}>
            No parameters available for this retriever.
          </Typography>
        )}

      {selectedRetriever && openConfig && (
        <FormSchemaContainer>
          <FormSchema
            model={selectedRetriever.name}
            initialValues={{
              ...selectedRetriever.parameters,
              ...(retrieverModel?.params || {}),
            }}
            autoSave={true}
            onFormSubmit={handleRetrieverParametersSave}
          />
        </FormSchemaContainer>
      )}
    </Box>
  );
}

RetrieverConfigurationStep.propTypes = {
  retrieverModel: PropTypes.object,
  setRetrieverModel: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};
