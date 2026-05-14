import {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
  forwardRef,
  useImperativeHandle,
} from "react";
import PropTypes from "prop-types";
import { Box, Autocomplete, TextField, Typography } from "@mui/material";

import {
  getRetrieverComponents,
  getRetrievalParadigm,
} from "../../../../api/rag";

import RAGFormSchema from "../components/RAGFormSchema";
import FormSchemaLayout from "../../../../components/shared/FormSchemaLayout";
import {
  FormSchemaProvider,
  useFormSchemaStore,
} from "../../../../contexts/schema";
import { getInitialModelParameters } from "../components/ragFormDefaults";

function FormSchemaInterceptor({ currentFormValuesRef }) {
  const store = useFormSchemaStore();

  useEffect(() => {
    if (store && store.formValues && currentFormValuesRef) {
      if (Object.keys(store.formValues).length > 0) {
        currentFormValuesRef.current = { ...store.formValues };
      }
    }
  }, [store?.formValues, currentFormValuesRef]);

  return null;
}



function AutoSaveFormSchema({
  selectedRetriever,
  retrieverModel,
  onParametersChange,
  currentFormValuesRef,
}) {
  const formikRef = useRef(null);

  const initialValues = useMemo(() => {
    return getInitialModelParameters({
      selectedModel: selectedRetriever,
      currentModelName: retrieverModel?.component,
      currentParams: retrieverModel?.params,
    });
  }, [
    selectedRetriever,
    retrieverModel?.component,
    retrieverModel?.params,
  ]);

  const handleFormSubmit = useCallback(
    (values) => {
      if (currentFormValuesRef) {
        currentFormValuesRef.current = values;
      }

      onParametersChange(values);
    },
    [onParametersChange, currentFormValuesRef],
  );

  return (
    <FormSchemaLayout>
      <FormSchemaInterceptor currentFormValuesRef={currentFormValuesRef} />
      <RAGFormSchema
        model={selectedRetriever.name}
        initialValues={initialValues}
        autoSave={true}
        onFormSubmit={handleFormSubmit}
        onCancel={undefined}
        formSubmitRef={formikRef}
      />
    </FormSchemaLayout>
  );
}

const RetrieverConfigurationStep = forwardRef(
  function RetrieverConfigurationStep(
    { retrieverModel, setRetrieverModel, setNextEnabled },
    ref,
  ) {
    const [retrievalParadigms, setRetrievalParadigms] = useState([]);
    const [selectedRetrievalParadigm, setSelectedRetrievalParadigm] =
      useState(null);

    const [retrieverOptions, setRetrieverOptions] = useState([]);
    const [selectedRetriever, setSelectedRetriever] = useState(null);
    const [openConfig, setOpenConfig] = useState(false);
    const [retrieversLoading, setRetrieversLoading] = useState(false);
    const currentFormValuesRef = useRef(null);

    const saveCurrentFormValues = useCallback(() => {
      let valuesToSave = currentFormValuesRef.current;
      console.log(
        "saveCurrentFormValues - currentFormValuesRef:",
        currentFormValuesRef.current,
      );

      if (!valuesToSave || Object.keys(valuesToSave).length === 0) {
        const formSchemaElement =
          document.querySelector('[data-testid="form-schema"]') ||
          document.querySelector("form");

        if (!valuesToSave || Object.keys(valuesToSave).length === 0) {
          const formData = extractFormDataFromDOM();
          console.log("formData extracted from DOM:", formData);
          if (formData && Object.keys(formData).length > 0) {
            valuesToSave = formData;
            currentFormValuesRef.current = formData;
          }
        }
      }

      if (
        valuesToSave &&
        Object.keys(valuesToSave).length > 0 &&
        selectedRetriever
      ) {
        setRetrieverModel({
          component: selectedRetriever.name,
          params: valuesToSave,
        });
      }
    }, [selectedRetriever, setRetrieverModel]);

    const extractFormDataFromDOM = () => {
      try {
        const allInputs = document.querySelectorAll("input, select, textarea");
        const formData = {};

        console.log("allInputs", allInputs);

        allInputs.forEach((input) => {
          const name = input.name || input.id || "";
          const value = input.value;

          if (name && value) {
            console.log("Processing input:", name, value);
            if (
              name.includes("similarity_metric") ||
              name.includes("similarity")
            ) {
              formData.similarity_metric = value;
            } else if (name.includes("top_k") || name.includes("topk")) {
              formData.top_k = parseInt(value) || 5;
            } else if (name.includes("model_name")) {
              console.log("Processing model_name:", name, value);
              if (!formData.encoding_model) {
                formData.encoding_model = {
                  properties: {
                    component: "DenseEmbedding",
                    params: {
                      comp: { component: "FastTextEmbedding", params: {} },
                    },
                  },
                };
              }
              formData.encoding_model.properties.params.comp.params.model_name =
                value;
            } else if (name.includes("pooling_strategy")) {
              if (!formData.encoding_model) {
                formData.encoding_model = {
                  properties: {
                    component: "DenseEmbedding",
                    params: {
                      comp: { component: "FastTextEmbedding", params: {} },
                    },
                  },
                };
              }
              formData.encoding_model.properties.params.comp.params.pooling_strategy =
                value;
            }
          }
        });

        return Object.keys(formData).length > 0 ? formData : null;
      } catch (error) {
        return null;
      }
    };
    useEffect(() => {
      return () => {
        saveCurrentFormValues();
      };
    }, [saveCurrentFormValues]);

    useImperativeHandle(
      ref,
      () => ({
        saveFormValues: saveCurrentFormValues,
      }),
      [saveCurrentFormValues],
    );

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
      } catch (error) {
        console.error("Error fetching retrieval paradigms:", error);
      }
    };

    useEffect(() => {
      fetchRetrievalParadigms();
    }, []);

    const fetchRetrievers = useCallback(async () => {
      if (!selectedRetrievalParadigm) {
        setRetrieverOptions([]);
        setSelectedRetriever(null);
        setOpenConfig(false);
        return;
      }

      setRetrieversLoading(true);
      if (selectedRetrievalParadigm.name === "SparseRetriever") {
        try {
          const retrievers = await getRetrieverComponents(
            selectedRetrievalParadigm.name,
          );
          const filteredRetrievers = retrievers.filter(
            (retriever) =>
              retriever?.name !== selectedRetrievalParadigm.name &&
              retriever?.configurable_object !== false,
          );
          setRetrieverOptions(filteredRetrievers);

          if (retrieverModel?.component) {
            const existingRetriever = filteredRetrievers.find(
              (r) => r.name === retrieverModel.component,
            );
            if (existingRetriever) {
              setSelectedRetriever(existingRetriever);
              setOpenConfig(Boolean(existingRetriever?.schema?.properties));
              setNextEnabled(true);
            } else {
              setSelectedRetriever(null);
              setOpenConfig(false);
            }
          } else {
            setSelectedRetriever(null);
            setOpenConfig(false);
          }
        } catch (error) {
          console.error("Error fetching sparse retrievers:", error);
          setRetrieverOptions([]);
          setSelectedRetriever(null);
          setOpenConfig(false);
        }
      } else {
        setRetrieverOptions([selectedRetrievalParadigm]);
        setSelectedRetriever(selectedRetrievalParadigm);
        setOpenConfig(Boolean(selectedRetrievalParadigm?.schema?.properties));
        setNextEnabled(true);
      }
      setRetrieversLoading(false);
    }, [selectedRetrievalParadigm, retrieverModel?.component, setNextEnabled]);

    useEffect(() => {
      fetchRetrievers();
    }, [selectedRetrievalParadigm, fetchRetrievers]);

    useEffect(() => {
      return () => {
        if (currentFormValuesRef.current && selectedRetriever) {
          handleRetrieverParametersSave(currentFormValuesRef.current);
        }
      };
    }, [selectedRetriever]);

    const handleRetrievalParadigmChange = (event, newValue) => {
      setSelectedRetrievalParadigm(newValue);
      
      // Clear current form values and retriever model when switching paradigms
      currentFormValuesRef.current = null;
      setRetrieverModel({
        component: "",
        params: {}
      });
      
      if (newValue?.name === "SparseRetriever") {
        setSelectedRetriever(null);
        setOpenConfig(false);
        setNextEnabled(false);
      } else if (newValue) {
        setRetrieverOptions([newValue]);
        setSelectedRetriever(newValue);
        setOpenConfig(Boolean(newValue?.schema?.properties));
        setRetrieverModel({
          component: newValue.name,
          params: getInitialModelParameters({
            selectedModel: newValue,
            currentModelName: null,
            currentParams: null,
          }),
        });
        setNextEnabled(true);
      } else {
        setSelectedRetriever(null);
        setOpenConfig(false);
        setNextEnabled(false);
      }
    };

    const handleRetrieverSelectionChange = (event, newValue) => {
      setSelectedRetriever(newValue);
      if (newValue) {
        setOpenConfig(Boolean(newValue?.schema?.properties));
        setNextEnabled(true);

        // Clear previous form values and use only the new retriever's default parameters
        currentFormValuesRef.current = null;
        setRetrieverModel({
          component: newValue.name,
          params: getInitialModelParameters({
            selectedModel: newValue,
            currentModelName: null,
            currentParams: null,
          }),
        });
      } else {
        setRetrieverModel({ component: "", params: {} });
        setOpenConfig(false);
        setNextEnabled(false);
      }
    };
    const handleRetrieverParametersSave = useCallback(
      (newParams) => {
        const newRetrieverModel = {
          component: selectedRetriever?.name || "",
          params: newParams,
        };

        setRetrieverModel(newRetrieverModel);
        setNextEnabled(true);
      },
      [selectedRetriever?.name, setRetrieverModel, setNextEnabled],
    );

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
                loading={retrieversLoading}
                getOptionLabel={(option) => option.name}
                noOptionsText={
                  retrieversLoading
                    ? "Loading retrievers..."
                    : "No retrievers available"
                }
                value={selectedRetriever}
                onChange={handleRetrieverSelectionChange}
                isOptionEqualToValue={(option, value) =>
                  option.name === value?.name
                }
                renderInput={(params) => (
                  <TextField
                    sx={{ mb: 3 }}
                    {...params}
                    label="Retriever model"
                  />
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
          <FormSchemaProvider key={`retriever-provider-${selectedRetriever.name}`}>
            <AutoSaveFormSchema
              key={`retriever-form-${selectedRetriever.name}`}
              selectedRetriever={selectedRetriever}
              retrieverModel={retrieverModel}
              onParametersChange={handleRetrieverParametersSave}
              currentFormValuesRef={currentFormValuesRef}
            />
          </FormSchemaProvider>
        )}
      </Box>
    );
  },
);

RetrieverConfigurationStep.propTypes = {
  retrieverModel: PropTypes.object,
  setRetrieverModel: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

export default RetrieverConfigurationStep;
