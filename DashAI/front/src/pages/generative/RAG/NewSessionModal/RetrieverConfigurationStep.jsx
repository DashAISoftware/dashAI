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

import FormSchema from "../../../../components/shared/FormSchema";
import FormSchemaLayout from "../../../../components/shared/FormSchemaLayout";
import {
  FormSchemaProvider,
  useFormSchemaStore,
} from "../../../../contexts/schema";

// Componente que intercepta valores del contexto de FormSchema
function FormSchemaInterceptor({ currentFormValuesRef }) {
  const store = useFormSchemaStore();

  useEffect(() => {
    if (store && store.formValues && currentFormValuesRef) {
      console.log("=== FORM SCHEMA STORE VALUES ===");
      console.log("Store formValues:", store.formValues);

      if (Object.keys(store.formValues).length > 0) {
        currentFormValuesRef.current = { ...store.formValues };
        console.log("Successfully captured from store:", store.formValues);
      }
    }
  }, [store?.formValues, currentFormValuesRef]);

  return null; // Este componente no renderiza nada
}

function AutoSaveFormSchema({
  selectedRetriever,
  retrieverModel,
  onParametersChange,
  currentFormValuesRef,
}) {
  const formikRef = useRef(null);

  const initialValues = useMemo(() => {
    const baseValues = selectedRetriever.parameters || {};
    return {
      ...baseValues,
      ...(retrieverModel?.params || {}),
    };
  }, [
    selectedRetriever.name,
    selectedRetriever.parameters,
    retrieverModel?.params,
  ]);

  // Enhanced form submit handler
  const handleFormSubmit = useCallback(
    (values) => {
      console.log("=== FORM SUBMIT HANDLER ===");
      console.log("Submitted values:", values);

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
      <FormSchema
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
    const currentFormValuesRef = useRef(null);

    const saveCurrentFormValues = useCallback(() => {
      console.log("=== SAVE CURRENT FORM VALUES CALLED ===");
      console.log("selectedRetriever:", selectedRetriever?.name);
      console.log(
        "currentFormValuesRef.current:",
        currentFormValuesRef.current,
      );

      let valuesToSave = currentFormValuesRef.current;

      // Si no tenemos valores en la ref, intentar capturar directamente del formik
      if (!valuesToSave || Object.keys(valuesToSave).length === 0) {
        console.log("No values in ref, trying to capture from formikRef...");
        const formSchemaElement =
          document.querySelector('[data-testid="form-schema"]') ||
          document.querySelector("form");
        if (formSchemaElement) {
          console.log("Found form element, attempting to extract values");
        }

        // Último recurso: construir valores desde el DOM
        if (!valuesToSave || Object.keys(valuesToSave).length === 0) {
          console.log("Attempting to extract values from DOM...");
          const formData = extractFormDataFromDOM();
          if (formData && Object.keys(formData).length > 0) {
            valuesToSave = formData;
            currentFormValuesRef.current = formData;
            console.log("Successfully extracted from DOM:", formData);
          }
        }
      }

      if (
        valuesToSave &&
        Object.keys(valuesToSave).length > 0 &&
        selectedRetriever
      ) {
        console.log("Saving parameters:", valuesToSave);
        setRetrieverModel({
          component: selectedRetriever.name,
          params: valuesToSave,
        });
        console.log("Parameters saved successfully");
      } else {
        console.warn("Cannot save - missing values or retriever");
        console.log("valuesToSave:", valuesToSave);
        console.log("selectedRetriever:", selectedRetriever);
      }
    }, [selectedRetriever, setRetrieverModel]);

    // Función helper para extraer datos del DOM como último recurso
    const extractFormDataFromDOM = () => {
      try {
        // Buscar todos los inputs y selects en el formulario
        const allInputs = document.querySelectorAll("input, select, textarea");
        const formData = {};

        allInputs.forEach((input) => {
          const name = input.name || input.id || "";
          const value = input.value;

          if (name && value) {
            // Similarity metric
            if (
              name.includes("similarity_metric") ||
              name.includes("similarity")
            ) {
              formData.similarity_metric = value;
            }
            // Top K
            else if (name.includes("top_k") || name.includes("topk")) {
              formData.top_k = parseInt(value) || 5;
            }
            // Model name for embeddings
            else if (name.includes("model_name")) {
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
            }
            // Pooling strategy
            else if (name.includes("pooling_strategy")) {
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

        console.log("Extracted form data from DOM:", formData);
        return Object.keys(formData).length > 0 ? formData : null;
      } catch (error) {
        console.error("Error extracting form data from DOM:", error);
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

    useEffect(() => {
      return () => {
        if (currentFormValuesRef.current && selectedRetriever) {
          handleRetrieverParametersSave(currentFormValuesRef.current);
        }
      };
    }, [selectedRetriever]);

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

        setRetrieverModel({
          component: newValue.name,
          params: retrieverModel?.params || {},
        });
      } else {
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
                getOptionLabel={(option) => option.name}
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
          <FormSchemaProvider>
            <AutoSaveFormSchema
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
